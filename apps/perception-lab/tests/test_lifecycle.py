import json
from dataclasses import replace

import pytest

from perception_lab.config import PreprocessConfig, Resolution
from perception_lab.contracts import Cancellation, DropReason, LabError
from perception_lab.geometry import CoreGeometry
from perception_lab.preprocessing import BasicPreprocessor
from perception_lab.scheduling import QueuedFrame
from perception_lab.sources import SyntheticSource


def test_explicit_source_scaling_restores_original_calibrated_pixels(calibration):
    geometry = CoreGeometry(calibration, source_scaling=Resolution(width=16, height=12))
    pre = BasicPreprocessor(
        geometry, PreprocessConfig(operation="crop", width=8, height=6, left=4, top=2)
    )
    output = pre.prepare(next(iter(SyntheticSource(iter([0]), width=16, height=12))))
    assert output.mapping.inverse(0.0, 0.0) == (2.0, 1.0)
    assert output.mapping.inverse(8.0, 6.0) == (6.0, 4.0)


def test_calibration_missing_required_geometry(calibration):
    from pydantic import ValidationError

    from perception_lab.config import Calibration

    raw = calibration.model_dump()
    del raw["intrinsics"]["skew"]
    with pytest.raises(ValidationError):
        Calibration.model_validate(raw)


def test_realtime_stale_frame_never_reaches_component(make_pipeline):
    pipeline, recorder = make_pipeline(
        {"mode": "REALTIME", "drop_policy": "LATEST_FRAME", "max_staleness_ns": 1}
    )
    frame = next(iter(SyntheticSource(iter([0]))))
    pipeline.process(QueuedFrame(frame, pipeline.clock(), 0))
    assert pipeline.metrics.drops == {DropReason.REALTIME_STALENESS.value: 1}
    assert pipeline.metrics.counts["processed"] == 0
    recorder.close()


def test_render_adapter_closed(make_pipeline):
    class Renderer:
        rendered = 0
        closed = False

        def render(self, *args):
            self.rendered += 1

        def close(self):
            self.closed = True

    renderer = Renderer()
    pipeline, _ = make_pipeline(renderer=renderer)
    pipeline.run(SyntheticSource(iter([0, 10])))
    assert renderer.rendered == 2 and renderer.closed
    assert pipeline.metrics.stages["render"].count == 2


def test_keyboard_interrupt_finalizes(make_pipeline):
    def listener(event):
        if event.kind == "ComponentStarted":
            raise KeyboardInterrupt()

    pipeline, recorder = make_pipeline({"record_session": True}, listener=listener)
    source = SyntheticSource(iter([0, 10]))
    with pytest.raises(KeyboardInterrupt):
        pipeline.run(source)
    assert source.closed and recorder.closed
    assert recorder.manifest["termination_reason"] == "CANCELLED"


def test_source_close_failure_is_fatal(make_pipeline):
    class Source(SyntheticSource):
        def close(self):
            super().close()
            raise OSError("private path")

    pipeline, recorder = make_pipeline({"record_session": True})
    with pytest.raises(LabError):
        pipeline.run(Source(iter([0])))
    assert recorder.closed
    assert (
        json.loads((recorder.directory / "manifest.json").read_text())["termination_reason"]
        == "FATAL"
    )


def test_source_identity_change_rejected(make_pipeline):
    class Source(SyntheticSource):
        def __iter__(self):
            for frame in super().__iter__():
                yield replace(
                    frame, identity=replace(frame.identity, source_id=str(frame.identity.sequence))
                )

    pipeline, recorder = make_pipeline()
    with pytest.raises(LabError):
        pipeline.run(Source(iter([0, 10])))
    assert recorder.closed


def test_pre_cancelled_session_closes_without_consuming(make_pipeline):
    pipeline, recorder = make_pipeline()
    source = SyntheticSource(iter([0]))
    manifest = pipeline.run(source, Cancellation(True))
    assert manifest["termination_reason"] == "CANCELLED"
    assert manifest["summary"]["frame_counts"]["source"] == 0
    assert source.closed and recorder.closed


@pytest.mark.parametrize("phase", ["iterator_open", "iterator_close"])
def test_iterator_lifecycle_failure_finalizes_all_resources(make_pipeline, phase):
    class Source:
        closed = False

        def __iter__(self):
            if phase == "iterator_open":
                raise RuntimeError("private path")
            return self

        def __next__(self):
            raise StopIteration

        def close(self):
            self.closed = True
            if phase == "iterator_close":
                raise RuntimeError("private path")

    pipeline, recorder = make_pipeline({"record_session": True})
    source = Source()
    with pytest.raises(LabError):
        pipeline.run(source)
    assert source.closed and recorder.closed
    assert recorder.manifest["termination_reason"] == "FATAL"


def test_failure_after_frame_completion_does_not_double_count(make_pipeline):
    def listener(event):
        if event.kind == "FrameCompleted":
            raise RuntimeError("listener failed")

    pipeline, recorder = make_pipeline(listener=listener)
    with pytest.raises(LabError):
        pipeline.run(SyntheticSource(iter([0])))
    counts = recorder.manifest["summary"]["frame_counts"]
    assert counts["processed"] == 1 and counts["dropped"] == 0


def test_failure_during_accept_does_not_double_count(make_pipeline):
    def listener(event):
        if event.kind == "FrameAccepted":
            raise RuntimeError("listener failed")

    pipeline, recorder = make_pipeline(listener=listener)
    with pytest.raises(LabError):
        pipeline.run(SyntheticSource(iter([0])))
    counts = recorder.manifest["summary"]["frame_counts"]
    assert counts["source"] == 1 and counts["dropped"] == 1


def test_cancellation_before_component_call_prevents_call(make_pipeline):
    from perception_lab.components import NoOpDetector

    cancel = Cancellation()

    class Detector(NoOpDetector):
        called = False

        def detect(self, image, identity):
            self.called = True
            return None

    detector = Detector()

    def listener(event):
        if event.kind == "ComponentStarted":
            cancel.cancel()

    pipeline, recorder = make_pipeline(listener=listener, detector=detector)
    pipeline.run(SyntheticSource(iter([0])), cancel)
    assert not detector.called
    assert recorder.manifest["summary"]["frame_counts"]["dropped"] == 1


def test_realtime_expiry_during_component_is_not_published(make_pipeline):
    from test_pipeline import SimulatedClock

    from perception_lab.components import NoOpDetector

    clock = SimulatedClock()

    class Detector(NoOpDetector):
        def detect(self, image, identity):
            clock.now += 1000
            return None

    class Source(SyntheticSource):
        def __iter__(self):
            for frame in super().__iter__():
                yield replace(frame, decode_started_ns=clock(), decode_completed_ns=clock())

    pipeline, recorder = make_pipeline(
        {"mode": "REALTIME", "drop_policy": "LATEST_FRAME", "max_staleness_ns": 100},
        detector=Detector(),
        clock=clock,
        sleep=clock.sleep,
    )
    pipeline.run(Source(iter([0])))
    summary = recorder.manifest["summary"]
    assert summary["frame_counts"]["processed"] == 0
    assert summary["drops"] == {"REALTIME_STALENESS": 1}


def test_metrics_write_failure_never_marks_session_success(make_pipeline):
    pipeline, recorder = make_pipeline({"record_session": True})
    (recorder.directory / "metrics.json").mkdir()
    with pytest.raises(LabError):
        pipeline.run(SyntheticSource(iter([0])))
    manifest = json.loads((recorder.directory / "manifest.json").read_text())
    assert manifest["termination_reason"] == "FATAL"
    assert recorder.closed
