from dataclasses import replace
from threading import Event
from time import monotonic, sleep

import pytest

from perception_lab.components import NoOpDetector
from perception_lab.config import LabConfig
from perception_lab.depth_synthetic import SyntheticDepthProvider
from perception_lab.enrichment_worker import EnrichmentWorker
from perception_lab.latest_source import LatestSource
from perception_lab.latest_worker import LatestWorker
from perception_lab.preprocessing import BasicPreprocessor
from perception_lab.scheduling import QueuedFrame
from perception_lab.sources import SyntheticSource


def await_result(worker):
    deadline = monotonic() + 5
    while monotonic() < deadline:
        result = worker.poll()
        if result is not None:
            return result
        sleep(0.001)
    pytest.fail("Worker did not finish")


def test_worker_keeps_only_latest_pending_and_preserves_timestamps():
    entered, release = Event(), Event()
    seen = []

    def infer(value):
        seen.append(value)
        if value == 0:
            entered.set()
            assert release.wait(5)
        return value * 2

    worker = LatestWorker(infer, "test-latest")
    try:
        worker.submit(0)
        assert entered.wait(5)
        for value in range(1, 101):
            worker.submit(value)
        assert worker.summary()["pending_replaced"] == 99
        assert worker.poll() is None
        release.set()
        result = await_result(worker)
        if result.input == 0:
            result = await_result(worker)
        assert result.input == 100 and result.output == 200
        assert result.submitted_ns <= result.started_ns <= result.completed_ns
        assert seen == [0, 100]
    finally:
        release.set()
        worker.close()
    assert worker.summary()["completed"] == 2
    with pytest.raises(RuntimeError):
        worker.submit(101)


def test_worker_failure_is_sticky_and_pending_work_is_cancelled():
    entered, release = Event(), Event()

    def infer(value):
        entered.set()
        assert release.wait(5)
        raise ValueError("provider failed")

    worker = LatestWorker(infer, "test-failure")
    try:
        worker.submit(0)
        assert entered.wait(5)
        worker.submit(1)
        release.set()
        with pytest.raises(ValueError, match="provider failed"):
            await_result(worker)
        with pytest.raises(ValueError, match="provider failed"):
            worker.poll()
        with pytest.raises(RuntimeError):
            worker.submit(2)
    finally:
        release.set()
        worker.close()
    assert worker.summary()["cancelled"] == 1


def test_unused_worker_close_is_idempotent():
    worker = LatestWorker(lambda x: x, "test-unused")
    worker.close()
    worker.close()
    assert worker.summary()["submitted"] == 0


def test_failure_during_shutdown_is_reported_even_without_another_poll():
    entered, release = Event(), Event()

    def fail(value):
        entered.set()
        assert release.wait(5)
        raise ValueError("late failure")

    worker = LatestWorker(fail, "test-late-error")
    worker.submit(1)
    assert entered.wait(5)
    release.set()
    with pytest.raises(ValueError, match="late failure"):
        worker.close()
    assert worker.summary()["failures"] == 1
    worker.close()


def test_latest_source_replacement_accounting_and_original_identity():
    source = LatestSource(SyntheticSource(iter(range(100))), 0, 100)
    try:
        iterator = iter(source)
        first = next(iterator)
        source._thread.join(5)
        assert not source._thread.is_alive()
        remaining = list(iterator)
        frames = [first, *remaining]
        assert frames[-1].identity.observation_ns == 99
        assert frames[-1].identity.sequence == 99
        assert len(frames) + source.replaced == source.decoded == 100
        assert len(remaining) <= 1
    finally:
        source.close()


def test_source_end_boundary_is_distinct_from_last_delivered_frame():
    source = LatestSource(SyntheticSource(iter(range(101))), 0, 100)
    try:
        frames = list(source)
        assert source.last_seen_ns == 100
        assert frames[-1].identity.observation_ns == 99
        assert source.decoded == 100
    finally:
        source.close()


def test_source_failure_after_last_consumed_frame_is_not_lost_on_close():
    entered, release = Event(), Event()

    class LateFailureSource:
        closed = False

        def __iter__(self):
            yield next(iter(SyntheticSource(iter([0]))))
            entered.set()
            assert release.wait(5)
            raise ValueError("late source failure")

        def close(self):
            self.closed = True

    underlying = LateFailureSource()
    source = LatestSource(underlying, 0, None)
    iterator = iter(source)
    try:
        assert next(iterator).identity.sequence == 0
        assert entered.wait(5)
        release.set()
        with pytest.raises(ValueError, match="late source failure"):
            source.close()
        assert underlying.closed
        source.close()
    finally:
        release.set()
        iterator.close()
        source.close()


def test_optional_worker_runs_during_detection_and_is_consumed_afterward(make_pipeline):
    entered = Event()

    class SignallingDepth(SyntheticDepthProvider):
        def estimate_depth(self, image, identity):
            entered.set()
            return super().estimate_depth(image, identity)

    class WaitingDetector(NoOpDetector):
        def detect(self, image, identity):
            assert entered.wait(5), "Enrichment must not wait for synchronous detection"
            worker = pipeline.enrichment_workers["depth"]
            completion = await_result(worker)
            with worker._condition:
                worker._ready = completion
            return None

    pipeline, recorder = make_pipeline(
        {
            "realtime_rescue": True,
            "mode": "REALTIME",
            "drop_policy": "LATEST_FRAME",
            "queue_capacity": 1,
            "max_staleness_ns": 10_000_000_000,
            "depth": {"provider": "synthetic"},
        },
        detector=WaitingDetector(),
        depth=SignallingDepth(),
    )
    frame = next(iter(SyntheticSource(iter([0]))))
    captured = []
    recorder.write_result = captured.append
    now = pipeline.clock()
    try:
        pipeline.process(QueuedFrame(frame, now, now))
        assert pipeline.metrics.counts["processed"] == 1
        assert captured[0].depth.identity == frame.identity
    finally:
        pipeline.enrichment_workers["depth"].close()
        recorder.close()


@pytest.mark.parametrize(
    "change",
    [
        {"mode": "OFFLINE_REPLAY"},
        {"queue_capacity": 2},
        {"drop_policy": "DROP_OLDEST"},
        {"visualization": True},
        {"record_session": True},
    ],
)
def test_rescue_configuration_rejects_incompatible_modes(config, change):
    raw = {
        **config.model_dump(),
        "realtime_rescue": True,
        "mode": "REALTIME",
        "drop_policy": "LATEST_FRAME",
        "queue_capacity": 1,
        "max_staleness_ns": 1000,
        **change,
    }
    with pytest.raises(ValueError):
        LabConfig.model_validate(raw)


def test_rescue_fast_path_runs_without_optional_providers(make_pipeline):
    pipeline, recorder = make_pipeline(
        {
            "realtime_rescue": True,
            "mode": "REALTIME",
            "drop_policy": "LATEST_FRAME",
            "queue_capacity": 1,
            "max_staleness_ns": 1_000_000_000,
        }
    )
    try:
        pipeline.run(SyntheticSource(iter([0, 1_000_000, 2_000_000])))
        assert pipeline.metrics.counts["processed"] >= 1
        assert pipeline.metrics.counts["failed"] == 0
        assert pipeline.enrichment_workers == {}
    finally:
        recorder.close()


def test_slow_depth_does_not_block_fast_path(make_pipeline):
    entered, release = Event(), Event()

    class SlowDepth(SyntheticDepthProvider):
        def estimate_depth(self, image, identity):
            entered.set()
            assert release.wait(5)
            return super().estimate_depth(image, identity)

    pipeline, recorder = make_pipeline(
        {
            "realtime_rescue": True,
            "mode": "REALTIME",
            "drop_policy": "LATEST_FRAME",
            "queue_capacity": 1,
            "max_staleness_ns": 10_000_000_000,
            "depth": {"provider": "synthetic"},
        },
        depth=SlowDepth(),
    )
    frame = next(iter(SyntheticSource(iter([0]))))
    now = pipeline.clock()
    try:
        pipeline.process(QueuedFrame(frame, now, now))
        assert entered.wait(5)
        assert pipeline.metrics.counts["processed"] == 1
        assert pipeline.enrichment_workers["depth"].summary()["completed"] == 0
    finally:
        release.set()
        pipeline.enrichment_workers["depth"].close()
        recorder.close()


@pytest.mark.parametrize("age,accepted", [(100_000_000, True), (2_000_000_000, False)])
def test_async_depth_keeps_original_frame_and_rejects_stale(
    make_pipeline, geometry, monkeypatch, age, accepted
):
    pipeline, recorder = make_pipeline(
        {
            "realtime_rescue": True,
            "mode": "REALTIME",
            "drop_policy": "LATEST_FRAME",
            "queue_capacity": 1,
            "max_staleness_ns": 10_000_000_000,
            "depth": {"provider": "synthetic"},
        },
        depth=SyntheticDepthProvider(),
    )
    frames = list(SyntheticSource(iter([0, age])))
    worker = pipeline.enrichment_workers["depth"]
    prepared = BasicPreprocessor(geometry, pipeline.config.preprocess).prepare(frames[0])
    captured = []
    recorder.write_result = captured.append
    try:
        worker.submit((prepared, frames[0].identity))
        completion = await_result(worker)
        with worker._condition:
            worker._ready = completion
        # Isolate validation of this older result from a new frame's completion.
        monkeypatch.setattr(worker, "submit", lambda _job: None)
        now = pipeline.clock()
        pipeline.process(QueuedFrame(frames[1], now, now))
        assert len(captured) == 1
        if accepted:
            assert captured[0].depth.identity == frames[0].identity
            assert captured[0].depth.identity != captured[0].identity
            assert captured[0].detection_depths == ()
        else:
            assert captured[0].depth is None
            assert pipeline.enrichment_rejections["depth"] == 1
    finally:
        worker.close()
        recorder.close()


def test_async_provider_wrong_identity_fails(geometry, config):
    frame = next(iter(SyntheticSource(iter([0]))))
    image = BasicPreprocessor(geometry, config.preprocess).prepare(frame)
    provider = SyntheticDepthProvider()

    def wrong(image, identity):
        return provider.estimate_depth(image, replace(identity, sequence=1))

    worker = EnrichmentWorker(wrong, "depth")
    try:
        worker.submit((image, frame.identity))
        with pytest.raises(Exception, match="ASYNC_COMPONENT_IDENTITY_OR_TYPE_MISMATCH"):
            await_result(worker)
    finally:
        worker.close()
