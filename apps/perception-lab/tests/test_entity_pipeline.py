"""Generic entities traverse actual reasoning stages; no risk gates are relaxed."""

from dataclasses import replace
from threading import Event as ThreadEvent
from time import monotonic, sleep

import pytest
from conftest import records
from test_world_model import spatial as spatial_fixture

from perception_lab.contracts import ComponentProvenance
from perception_lab.detection import Box
from perception_lab.entity_compatibility import legacy_batch
from perception_lab.perceived_entity import (
    PerceivedEntityObservation,
    SemanticConcept,
    normalized_concept,
)
from perception_lab.sources import SyntheticSource
from perception_lab.tracking import AssociationTracker

spatial = spatial_fixture


def test_async_semantics_does_not_block_pipeline(make_pipeline, geometry):
    started, release = ThreadEvent(), ThreadEvent()

    class BlockedEnricher:
        def enrich(self, request):
            started.set()
            assert release.wait(5), "Pipeline waited for semantic inference"
            return request.observation

    completed = []

    def listener(event):
        if event.kind == "FrameCompleted":
            completed.append(event.identity.sequence)
            if len(completed) == 1:
                assert started.wait(5)
            if len(completed) == 12:
                release.set()

    pipeline, recorder = make_pipeline(
        {
            "record_session": True,
            "intervals_ns": {"detector": 100_000_000},
            "detector": {"weights": "unused.pt", "sha256": "a" * 64},
            "tracker": {"minimum_hits": 2},
            "world_model": {},
        },
        detector=EntityDetector(None),
        motion_geometry=geometry,
        semantic_enricher=BlockedEnricher(),
        listener=listener,
    )
    pipeline.tracker = AssociationTracker(
        pipeline.config.tracker, recorder.session_id, "synthetic", 8, 6, objectness_first=True
    )
    try:
        pipeline.run(SyntheticSource(iter(i * 100_000_000 for i in range(12))))
    finally:
        release.set()
    assert completed == list(range(12))
    frames = [row for row in records(recorder) if row["type"] == "frame_result"]
    assert all(not frame["errors"] for frame in frames)
    worker = pipeline.entity_semantic_worker.worker
    assert worker.summary()["pending_replaced"] >= 1
    assert not worker._thread.is_alive()


def test_async_semantics_applies_to_original_entity(make_pipeline, geometry):
    class Enricher:
        def enrich(self, request):
            return replace(
                request.observation,
                provider_id="semantic-fixture",
                concept=SemanticConcept("bollard", "bollard", 0.95, "fixture", "fixture", "1"),
            )

    def listener(event):
        if event.kind == "FrameCompleted" and event.identity.sequence == 0:
            # Synchronize the test only; the runtime never waits for completion.
            deadline = monotonic() + 5
            while pipeline.entity_semantic_worker.worker.summary()["completed"] == 0:
                assert monotonic() < deadline
                sleep(0.001)

    pipeline, recorder = make_pipeline(
        {
            "record_session": True,
            "intervals_ns": {"detector": 100_000_000},
            "detector": {"weights": "unused.pt", "sha256": "a" * 64},
            "tracker": {"minimum_hits": 2},
            "world_model": {},
        },
        detector=EntityDetector(None),
        motion_geometry=geometry,
        semantic_enricher=Enricher(),
        listener=listener,
    )
    pipeline.tracker = AssociationTracker(
        pipeline.config.tracker, recorder.session_id, "synthetic", 8, 6, objectness_first=True
    )
    pipeline.run(SyntheticSource(iter([0, 100_000_000])))
    frames = [row for row in records(recorder) if row["type"] == "frame_result"]
    assert all(not frame["errors"] for frame in frames)
    first, second = [frame["world_state"]["entities"][0] for frame in frames]
    assert first["entity_id"] == second["entity_id"]
    evidence = second["track_semantics"]["evidence"]
    enriched = [
        e["observation"] for e in evidence if e["observation"]["provider_id"] == "semantic-fixture"
    ]
    assert len(enriched) == 1
    assert enriched[0]["source_frame"]["sequence"] == 0
    assert enriched[0]["concept"]["raw_label"] == "bollard"
    assert pipeline._entity_semantic_applied == 1


def test_optional_provider_failure_preserves_unknown_entities_and_frame_processing(
    make_pipeline, geometry
):
    calls = []

    class FailedEnricher:
        def enrich(self, request):
            calls.append(request)
            raise RuntimeError("private provider context must not reach records")

    def listener(event):
        if event.kind == "FrameCompleted" and event.identity.sequence == 0:
            deadline = monotonic() + 5
            while not pipeline.entity_semantic_worker.provider_failed:
                assert monotonic() < deadline
                sleep(0.001)

    pipeline, recorder = make_pipeline(
        {
            "record_session": True,
            "intervals_ns": {"detector": 100_000_000},
            "detector": {"weights": "unused.pt", "sha256": "a" * 64},
            "tracker": {"minimum_hits": 2},
            "world_model": {},
        },
        detector=EntityDetector(None),
        motion_geometry=geometry,
        semantic_enricher=FailedEnricher(),
        listener=listener,
    )
    pipeline.tracker = AssociationTracker(
        pipeline.config.tracker, recorder.session_id, "synthetic", 8, 6, objectness_first=True
    )
    pipeline.run(SyntheticSource(iter(i * 100_000_000 for i in range(12))))
    rows = records(recorder)
    frames = [row for row in rows if row["type"] == "frame_result"]
    assert len(frames) == 12 and len(calls) == 1
    assert all(not frame["errors"] for frame in frames)
    assert all(frame["world_state"]["entities"] for frame in frames)
    assert all("ENTITY_SEMANTIC_PROVIDER_UNAVAILABLE" in frame["warnings"] for frame in frames[1:])
    assert "private provider context" not in str(rows)
    assert pipeline.entity_semantic_worker.timing()["provider_failed"]
    assert not pipeline.entity_semantic_worker.worker._thread.is_alive()


class EntityDetector:
    provenance = ComponentProvenance("generic-fixture", "detector")

    def __init__(self, label):
        self.label = label

    def detect(self, image, identity):
        concept = (
            None
            if self.label is None
            else SemanticConcept(
                self.label, normalized_concept(self.label), 0.9, "fixture", "fixture", "1"
            )
        )
        observation = PerceivedEntityObservation(
            f"region-{identity.sequence}",
            identity,
            Box(2 + 0.05 * identity.sequence, 1, 5 + 0.05 * identity.sequence, 5),
            0.9,
            None,
            "JOINT_DETECTION_SCORE",
            concept,
            None,
            "PHYSICAL_OBJECT_CANDIDATE" if concept else "UNKNOWN_PHYSICAL_OBJECT",
            image.mapping.fingerprint,
            "GOOD",
            "fixture",
            "1",
        )
        return legacy_batch(identity, (observation,), self.provenance, image.mapping.fingerprint)


@pytest.mark.parametrize("label", ["bollard", None, "electric scooter"])
def test_generic_entity_survives_complete_pipeline(make_pipeline, geometry, label):
    pipeline, recorder = make_pipeline(
        {
            "record_session": True,
            "intervals_ns": {"detector": 100_000_000},
            "detector": {"weights": "unused.pt", "sha256": "a" * 64, "confidence": 0.1},
            "tracker": {"minimum_hits": 2},
            "world_model": {},
            "corridor": {},
            "trajectory": {},
            "interaction": {},
            "risk": {},
            "attention": {},
            "alerts": {},
        },
        detector=EntityDetector(label),
        motion_geometry=geometry,
    )
    pipeline.tracker = AssociationTracker(
        pipeline.config.tracker, recorder.session_id, "synthetic", 8, 6, objectness_first=True
    )
    pipeline.run(SyntheticSource(iter(i * 100_000_000 for i in range(12))))
    frames = [row for row in records(recorder) if row["type"] == "frame_result"]
    final = frames[-1]
    assert len(frames) == 12 and all(not f["errors"] for f in frames)
    track = final["tracks"]["tracks"][0]
    entity = final["world_state"]["entities"][0]
    assert track["category"] == entity["category"] == "UNKNOWN"
    assert track["lifecycle"] == "CONFIRMED"
    assert entity["source_track_id"] == track["track_id"]
    assert entity["entity_observation"] == track["entity_observation"]
    concept = entity["entity_observation"]["concept"]
    assert (concept["raw_label"] if concept else None) == label
    semantics = entity["track_semantics"]
    assert semantics["quality"] == ("STABLE" if label else "UNKNOWN")
    assert semantics["track_id"] == track["track_id"]
    entity_id = entity["entity_id"]
    for component, field in [
        ("corridor_analysis", "entity_relations"),
        ("trajectory_set", "trajectories"),
        ("interaction_analysis", "entity_interactions"),
        ("risk_assessment_set", "assessments"),
    ]:
        assert any(item["entity_id"] == entity_id for item in final[component][field]), (
            component,
            final[component],
        )
    attention = final["attention_decision_set"]
    decisions = attention["selected"] + [item["decision"] for item in attention["suppressed"]]
    assert any(decision["entity_id"] == entity_id for decision in decisions)
    assert final["alert_output_set"]["outputs"]
    # Semantics may change wording, never the risk/attention admission policy.
    for frame in frames:
        for output in frame["alert_output_set"]["outputs"]:
            if output["presentation"]:
                expected = ["Object"] if label is None else ["Object", label.capitalize()]
                assert any(output["presentation"]["speech_text"].startswith(x) for x in expected)


def test_compatibility_adapter_rejects_wrong_frame(geometry):
    frame = next(iter(SyntheticSource(iter([100]))))
    from perception_lab.config import PreprocessConfig
    from perception_lab.preprocessing import BasicPreprocessor

    batch = EntityDetector(None).detect(
        BasicPreprocessor(geometry, PreprocessConfig()).prepare(frame), frame.identity
    )
    with pytest.raises(ValueError, match="frame/transform"):
        legacy_batch(
            replace(frame.identity, sequence=1),
            (batch.detections[0].entity_observation,),
            batch.provenance,
            batch.transform_hash,
        )


@pytest.mark.parametrize("height,metric", [(1.0, True), (0.0, False), (2.0, False)])
def test_generic_metric_relation_requires_plane_proximity(spatial, height, metric):
    from test_corridor import scene

    from perception_lab.corridor import HybridCorridorAnalyzer
    from perception_lab.corridor_config import CorridorConfig
    from perception_lab.detection import ObjectClass

    state = scene(spatial, metric=True)
    entity = state.entities[0]
    identity = entity.track_evidence.identity
    observation = PerceivedEntityObservation(
        "unknown-region",
        identity,
        entity.image_geometry,
        0.9,
        None,
        "JOINT_DETECTION_SCORE",
        None,
        None,
        "UNKNOWN_PHYSICAL_OBJECT",
        "a" * 64,
        "GOOD",
        "fixture",
        "1",
    )
    entity = replace(
        entity,
        category=ObjectClass.UNKNOWN,
        entity_observation=observation,
        position_camera=replace(entity.position_camera, position_meters=(0.0, height, 2.0)),
    )
    output = HybridCorridorAnalyzer(CorridorConfig(), spatial).analyze(
        replace(state, entities=(entity,))
    )
    relation = output.entity_relations[0]
    assert ("POINT_NEAR_SUPPLIED_GROUND_PLANE" in relation.assumptions) == metric
    assert "GROUNDED_CLASS_ASSUMPTION" not in relation.assumptions
    if not metric:
        assert relation.coordinate_basis == "IMAGE_SPACE_RELATION"
