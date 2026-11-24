from dataclasses import replace
from threading import Event

import pytest
from test_corridor import scene

from perception_lab.config import PreprocessConfig
from perception_lab.entity_enrichment import EntitySemanticWorker, SemanticEnrichmentRequest
from perception_lab.perceived_entity import PerceivedEntityObservation
from perception_lab.preprocessing import BasicPreprocessor
from perception_lab.sources import SyntheticSource
from perception_lab.world_types import WorldEntityId


def request_and_state(geometry):
    state = scene(geometry)
    entity = state.entities[0]
    frame = next(iter(SyntheticSource(iter([0]))))
    image = BasicPreprocessor(geometry, PreprocessConfig()).prepare(frame)
    observation = PerceivedEntityObservation(
        "region",
        frame.identity,
        entity.image_geometry,
        0.9,
        None,
        "JOINT_DETECTION_SCORE",
        None,
        None,
        "UNKNOWN_PHYSICAL_OBJECT",
        image.mapping.fingerprint,
        "GOOD",
        "fixture",
        "1",
    )
    return SemanticEnrichmentRequest(
        entity.entity_id, entity.source_track_id, observation, image, "NEW_TRACK"
    ), state


def completed(worker, count=1):
    # Condition coordination, not a wall-clock performance assertion.
    from time import monotonic, sleep

    deadline = monotonic() + 5
    while worker.worker.summary()["completed"] < count:
        if monotonic() >= deadline:
            pytest.fail("Worker did not complete")
        sleep(0.001)


def test_active_job_does_not_block_submission_and_pending_keeps_newest(geometry):
    request, state = request_and_state(geometry)
    entered, release = Event(), Event()
    calls = []

    class Provider:
        def enrich(self, job):
            calls.append(job.observation.observation_id)
            if len(calls) == 1:
                entered.set()
                assert release.wait(5)
            return job.observation

    worker = EntitySemanticWorker(Provider())
    try:
        worker.submit(request)
        assert entered.wait(5)
        for i in range(10):
            worker.submit(
                replace(
                    request, observation=replace(request.observation, observation_id=f"region-{i}")
                )
            )
        assert worker.worker.summary()["completed"] == 0
        assert worker.worker.summary()["pending_replaced"] == 9
        release.set()
        completed(worker, 2)
        result = worker.poll(state)
        assert calls == ["region", "region-9"]
        assert result.observation.observation_id == "region-9"
        assert result.compute_ns >= 0 and result.queue_wait_ns >= 0 and result.result_age_ns >= 0
    finally:
        release.set()
        worker.close()


@pytest.mark.parametrize("change", ["new_entity", "new_track", "new_source", "expired"])
def test_late_result_cannot_attach_to_replacement_or_stale_state(geometry, change):
    request, state = request_and_state(geometry)

    class Provider:
        def enrich(self, job):
            return job.observation

    worker = EntitySemanticWorker(Provider())
    try:
        worker.submit(request)
        completed(worker)
        entity = state.entities[0]
        if change == "new_entity":
            entity = replace(entity, entity_id=WorldEntityId("test", 99))
        elif change == "new_track":
            entity = replace(entity, source_track_id=replace(entity.source_track_id, serial=99))
        elif change == "new_source":
            entity = replace(
                entity,
                track_evidence=replace(
                    entity.track_evidence,
                    identity=replace(entity.track_evidence.identity, source_id="other"),
                ),
            )
        else:
            state = replace(state, state_timestamp=2_000_000_000)
        assert worker.poll(replace(state, entities=(entity,))) is None
        assert worker.rejected == 1
    finally:
        worker.close()


def test_failure_is_observable_and_no_geometry_mutation_allowed(geometry):
    request, state = request_and_state(geometry)
    returned = Event()

    class Provider:
        def enrich(self, job):
            returned.set()
            return replace(
                job.observation, source_frame=replace(job.observation.source_frame, sequence=99)
            )

    worker = EntitySemanticWorker(Provider())
    worker.submit(request)
    assert returned.wait(5)
    with pytest.raises(ValueError, match="source association"):
        worker.close()
