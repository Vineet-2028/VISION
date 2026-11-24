"""An unusable view is published as unavailable, not a confident empty scene."""

from dataclasses import replace

from conftest import records

from perception_lab.camera_view_quality import ViewStatus
from perception_lab.components import NoOpDetector
from perception_lab.sources import SyntheticSource


def test_black_view_skips_inference_and_publishes_unavailability(make_pipeline):
    class ForbiddenDetector(NoOpDetector):
        def detect(self, *_):
            raise AssertionError("Unusable view must not invoke detector")

    pipeline, recorder = make_pipeline(
        {"record_session": True, "camera_view_health": True, "world_model": {}},
        detector=ForbiddenDetector(),
    )
    result = pipeline.run(SyntheticSource(iter([0, 100_000_000]), width=64, height=48))
    frames = [r for r in records(recorder) if r["type"] == "frame_result"]
    assert len(frames) == 2
    assert result["summary"]["frame_counts"]["processed"] == 2
    assert result["summary"]["frame_counts"]["failed"] == 0
    for frame in frames:
        assert frame["schema_version"] == 13
        assert frame["scene_capability"] == "CAMERA_UNUSABLE"
        assert frame["camera_view_quality"]["status"] == "UNUSABLE"
        assert frame["world_state"]["scene_quality"]["state"] == "UNAVAILABLE"
        assert all(c["status"] == "UNAVAILABLE" for c in frame["world_state"]["capabilities"])
        assert frame["detector"] is None
        assert frame["risk_assessment_set"] is None
        assert frame["alert_output_set"] is None


def test_view_recovery_resumes_inference_without_reusing_unavailable_output(make_pipeline):
    calls = []

    class Detector(NoOpDetector):
        def detect(self, image, identity):
            calls.append(identity.sequence)
            return super().detect(image, identity)

    pipeline, recorder = make_pipeline(
        {"record_session": True, "camera_view_health": True}, detector=Detector()
    )
    estimator = pipeline.view_estimator

    class ControlledView:
        def estimate(self, frame):
            view = estimator.estimate(frame)
            return replace(view, status=ViewStatus.GOOD) if frame.identity.sequence == 1 else view

    pipeline.view_estimator = ControlledView()
    result = pipeline.run(SyntheticSource(iter([0, 100_000_000, 200_000_000])))
    assert calls == [1]
    assert result["summary"]["frame_counts"]["processed"] == 3
    frames = [r for r in records(recorder) if r["type"] == "frame_result"]
    assert [f["scene_capability"] for f in frames] == [
        "PERCEPTION_UNAVAILABLE",
        "DEGRADED",
        "PERCEPTION_UNAVAILABLE",
    ]
    assert [f["identity"]["observation_ns"] for f in frames] == [0, 100_000_000, 200_000_000]
