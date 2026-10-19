import gc
import json
import time
import weakref
from dataclasses import replace

import pytest
from conftest import records

from perception_lab.components import DetectionOutput, NoOpDetector
from perception_lab.contracts import (
    Cancellation,
    DropReason,
    FailureSeverity,
    LabError,
    SourceIssue,
)
from perception_lab.sources import SyntheticSource


def test_offline_end_to_end_recording(make_pipeline):
    pipeline, recorder = make_pipeline({"record_session": True})
    source = SyntheticSource(iter([0, 10, 20, 40]))
    manifest = pipeline.run(source)
    assert manifest["termination_reason"] == "END_OF_STREAM"
    assert manifest["summary"]["frame_counts"] == {
        "source": 4,
        "decoded": 4,
        "accepted": 4,
        "processed": 4,
        "dropped": 0,
        "failed": 0,
    }
    results = [r for r in records(recorder) if r["type"] == "frame_result"]
    assert [r["identity"]["observation_ns"] for r in results] == [0, 10, 20, 40]
    assert all(
        r["detector"] is None
        and r["depth"] is None
        and r["segmentation"] is None
        and r["optical_flow"] is None
        for r in results
    )
    assert all(
        c["identity"] == r["identity"]
        and c["status"] == "NO_OUTPUT"
        and c["provenance"]["model_id"] is None
        for r in results
        for c in r["components"]
    )
    assert recorder.closed and source.closed
    assert (
        json.loads((recorder.directory / "manifest.json").read_text())["summary"]
        == manifest["summary"]
    )
    assert sorted(p.name for p in recorder.directory.iterdir()) == [
        "frames.jsonl",
        "manifest.json",
        "metrics.json",
    ]
    assert "C:" not in (recorder.directory / "manifest.json").read_text()


def test_deterministic_semantics(make_pipeline):
    runs = []
    ids = []
    for _ in range(2):
        pipeline, recorder = make_pipeline({"record_session": True})
        pipeline.run(SyntheticSource(iter([0, 4, 12, 15, 99])))
        runs.append(
            [
                (r["identity"], [(c["provenance"], c["status"]) for c in r["components"]])
                for r in records(recorder)
                if r["type"] == "frame_result"
            ]
        )
        ids.append(recorder.session_id)
    assert runs[0] == runs[1]
    assert ids[0] != ids[1]


def test_default_no_recording(make_pipeline, tmp_path):
    pipeline, recorder = make_pipeline()
    pipeline.run(SyntheticSource(iter([0])))
    assert recorder.directory is None
    assert list(tmp_path.iterdir()) == []


def test_debug_storage_is_sampled_and_bounded(make_pipeline):
    pipeline, recorder = make_pipeline(
        {"record_session": True, "debug_every_n": 2, "debug_max_frames": 2}
    )
    pipeline.run(SyntheticSource(iter(range(10))))
    assert sorted(p.name for p in recorder.directory.glob("*.ppm")) == [
        "debug-0.ppm",
        "debug-2.ppm",
    ]


def test_duplicate_backward_and_range_drops(make_pipeline):
    pipeline, _ = make_pipeline({"start_ns": 5, "end_ns": 30})
    result = pipeline.run(SyntheticSource(iter([0, 10, 10, 9, 20, 30, 40])))
    assert result["summary"]["drops"] == {"USER_SKIP": 2, "INVALID_TIMESTAMP": 2}
    assert result["summary"]["frame_counts"]["processed"] == 2


class SimulatedClock:
    def __init__(self):
        self.now = time.monotonic_ns()

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += max(1, round(seconds * 1e9))


def test_slow_decoder_does_not_starve_processing(make_pipeline):
    clock = SimulatedClock()
    completed = []

    def listener(event):
        if event.kind == "FrameCompleted":
            completed.append(event.identity.sequence)

    class SlowSource(SyntheticSource):
        def __iter__(self):
            for frame in super().__iter__():
                clock.now += 101
                yield replace(frame, decode_started_ns=clock(), decode_completed_ns=clock())

    pipeline, _ = make_pipeline(
        {
            "mode": "REALTIME",
            "drop_policy": "LATEST_FRAME",
            "queue_capacity": 1,
            "max_staleness_ns": 500,
        },
        listener=listener,
        clock=clock,
        sleep=clock.sleep,
    )
    result = pipeline.run(SlowSource(iter(range(0, 10000, 100))))
    assert completed and completed[0] < 32
    counts = result["summary"]["frame_counts"]
    assert counts["processed"] + counts["dropped"] == 100
    assert result["summary"]["peak_queue_depth"] == 1


def test_realtime_result_age_uses_replay_anchor_not_media_clock(make_pipeline, monkeypatch):
    from perception_lab.detection import DetectionBatch

    clock = SimulatedClock()
    monkeypatch.setattr("perception_lab.sources.processing_ns", clock)

    class MeasuredDetector(NoOpDetector):
        def detect(self, image, identity):
            clock.now += 50
            return DetectionBatch(identity, (), self.provenance, image.mapping.fingerprint, 50, 0)

    pipeline, _ = make_pipeline(
        {
            "mode": "REALTIME",
            "drop_policy": "LATEST_FRAME",
            "max_staleness_ns": 1000,
            "intervals_ns": {"detector": 10},
        },
        clock=clock,
        sleep=clock.sleep,
        detector=MeasuredDetector(),
    )
    # Media begins far from the process clock. Raw subtraction would be nonsensical.
    result = pipeline.run(SyntheticSource(iter([700_000_000_000])))
    timing = result["summary"]["timing"]["realtime_detector_result_age"]
    assert timing["count"] == 1
    assert timing["p95_ns"] == 50


@pytest.mark.parametrize(
    "mode,policy",
    [("OFFLINE_REPLAY", "PROCESS_ALL"), ("REALTIME", "DROP_OLDEST"), ("REALTIME", "LATEST_FRAME")],
)
def test_slow_consumer_controlled_clock(make_pipeline, mode, policy):
    clock = SimulatedClock()
    completed = []

    def listener(event):
        if event.kind == "FrameCompleted":
            completed.append(event.identity.sequence)
            clock.now += 1000

    pipeline, _ = make_pipeline(
        {"mode": mode, "drop_policy": policy, "max_staleness_ns": 200, "queue_capacity": 2},
        listener=listener,
        clock=clock,
        sleep=clock.sleep,
    )

    class Source(SyntheticSource):
        def __iter__(self):
            for frame in super().__iter__():
                yield replace(frame, decode_started_ns=clock(), decode_completed_ns=clock())

    result = pipeline.run(Source(iter(range(0, 5000, 100))))
    counts = result["summary"]["frame_counts"]
    assert counts["processed"] + counts["dropped"] == 50
    assert result["summary"]["peak_queue_depth"] <= 2
    if mode == "OFFLINE_REPLAY":
        assert counts["processed"] == 50 and counts["dropped"] == 0
    else:
        assert counts["dropped"] > 0
        assert completed == sorted(completed)


def test_cancel_mid_session_closes_and_flushes(make_pipeline):
    cancel = Cancellation()

    def listener(event):
        if event.kind == "FrameCompleted":
            cancel.cancel()

    pipeline, recorder = make_pipeline({"record_session": True}, listener=listener)
    source = SyntheticSource(iter(range(100)))
    result = pipeline.run(source, cancel)
    assert result["termination_reason"] == "CANCELLED"
    assert result["summary"]["frame_counts"]["processed"] == 1
    assert source.closed and recorder.closed and not pipeline.queue.items


@pytest.mark.parametrize(
    "failure_at", ["source", "scheduler", "preprocess", "recorder", "listener", "component"]
)
def test_fatal_failures_cleanup(make_pipeline, monkeypatch, failure_at):
    pipeline, recorder = make_pipeline({"record_session": True})
    source = SyntheticSource(iter(range(3)))

    def fail(*args):
        raise RuntimeError("private C:/Users/name/input.mov")

    if failure_at == "source":

        def fail_source():
            raise RuntimeError("private source path")
            yield

        source.timestamps = fail_source()
    elif failure_at == "scheduler":
        monkeypatch.setattr(pipeline.scheduler, "eligible", fail)
    elif failure_at == "preprocess":
        monkeypatch.setattr(pipeline.preprocessor, "prepare", fail)
    elif failure_at == "recorder":
        monkeypatch.setattr(recorder, "write_result", fail)
    elif failure_at == "listener":
        pipeline.listener = fail
    else:
        monkeypatch.setattr(pipeline.detector, "detect", fail)
    with pytest.raises(LabError):
        pipeline.run(source)
    assert source.closed and recorder.closed and not pipeline.queue.items
    text = (recorder.directory / "manifest.json").read_text()
    assert json.loads(text)["termination_reason"] == "FATAL"
    assert "private" not in text


def test_recoverable_component_failure(make_pipeline):
    class FailedDetector(NoOpDetector):
        def detect(self, image, identity):
            raise LabError("model failed", FailureSeverity.RECOVERABLE)

    pipeline, recorder = make_pipeline({"record_session": True}, detector=FailedDetector())
    result = pipeline.run(SyntheticSource(iter([0, 10])))
    assert result["summary"]["frame_counts"]["processed"] == 2
    assert result["summary"]["frame_counts"]["failed"] == 2
    assert all(
        r["errors"] == ["detector:COMPONENT_RECOVERABLE"]
        for r in records(recorder)
        if r["type"] == "frame_result"
    )


def test_stale_component_identity_is_fatal(make_pipeline):
    class WrongDetector(NoOpDetector):
        def detect(self, image, identity):
            return DetectionOutput(
                replace(identity, sequence=99), (), self.provenance, "0" * 64, 0, 0
            )

    pipeline, recorder = make_pipeline(detector=WrongDetector())
    with pytest.raises(LabError):
        pipeline.run(SyntheticSource(iter([0])))
    assert recorder.manifest["termination_reason"] == "FATAL"


def test_source_issues_counted(make_pipeline):
    class Source(SyntheticSource):
        def __iter__(self):
            yield SourceIssue(0, DropReason.DECODE_FAILURE)
            yield SourceIssue(1, DropReason.CORRUPT_FRAME)
            yield from super().__iter__()

    pipeline, _ = make_pipeline()
    result = pipeline.run(Source(iter([0])))
    assert result["summary"]["frame_counts"] == {
        "source": 3,
        "decoded": 1,
        "accepted": 1,
        "processed": 1,
        "dropped": 2,
        "failed": 2,
    }


def test_long_run_releases_frames_and_bounds_metrics(make_pipeline):
    refs = []

    class Source(SyntheticSource):
        def __iter__(self):
            for frame in super().__iter__():
                if frame.identity.sequence % 500 == 0:
                    refs.append(weakref.ref(frame))
                yield frame

    pipeline, recorder = make_pipeline({"metrics_window": 16, "record_session": True})
    result = pipeline.run(Source(iter(range(5000))))
    gc.collect()
    assert all(ref() is None for ref in refs)
    assert all(len(stage.samples) <= 16 for stage in pipeline.metrics.stages.values())
    assert result["summary"]["frame_counts"]["processed"] == 5000
    assert not pipeline.queue.items and recorder.closed
