import pytest
from conftest import records

from perception_lab.contracts import ComponentProvenance, FailureSeverity, LabError
from perception_lab.detection import Box, Detection, DetectionBatch, ObjectClass
from perception_lab.sources import SyntheticSource


class FixtureDetector:
    provenance = ComponentProvenance("replaceable-fixture", "detector")

    def __init__(self, fail=False):
        self.fail = fail

    def detect(self, image, identity):
        if self.fail and identity.observation_ns == 200_000_000:
            raise LabError("INFERENCE", FailureSeverity.RECOVERABLE)
        ds = (
            ()
            if identity.observation_ns == 300_000_000
            else (Detection(0, "person", ObjectClass.PERSON, 0.9, Box(1, 1, 3, 4)),)
        )
        return DetectionBatch(identity, ds, self.provenance, image.mapping.fingerprint, 0, 0)


@pytest.mark.parametrize("fail", [False, True])
def test_pipeline_predicts_unscheduled_and_records_distinct_evidence(make_pipeline, fail):
    pipeline, recorder = make_pipeline(
        {
            "record_session": True,
            "intervals_ns": {"detector": 100_000_000},
            "detector": {"weights": "unused.pt", "sha256": "a" * 64, "confidence": 0.1},
            "tracker": {"minimum_hits": 2},
        },
        detector=FixtureDetector(fail),
    )
    pipeline.run(SyntheticSource(iter([0, 100_000_000, 150_000_000, 200_000_000, 300_000_000])))
    frames = [r for r in records(recorder) if r["type"] == "frame_result"]
    track_sets = [r["tracks"] for r in frames]
    assert [r["detector_evidence"] for r in track_sets] == [
        "SUCCESS",
        "SUCCESS",
        "NO_DETECTOR_RUN",
        "FAILURE" if fail else "SUCCESS",
        "SUCCESS_EMPTY",
    ]
    assert track_sets[2]["tracks"][0]["observation_status"] == "PREDICTED"
    assert track_sets[2]["tracks"][0]["misses"] == 0
    assert track_sets[3]["tracks"][0]["latest_failure"] == ("INFERENCE_FAILURE" if fail else None)
    assert len({r["tracks"][0]["track_id"]["serial"] for r in track_sets}) == 1
    assert all(r["schema_version"] == 2 for r in frames)
    assert recorder.manifest["summary"]["tracking_peaks"]["active"] == 1
    assert pipeline.tracker._closed
    assert pipeline.tracker._tracks == []


def test_tracker_closes_on_source_failure(make_pipeline):
    class BrokenSource(SyntheticSource):
        def __iter__(self):
            yield from super().__iter__()
            raise RuntimeError("private error")

    pipeline, _ = make_pipeline(
        {
            "detector": {"weights": "unused.pt", "sha256": "a" * 64, "confidence": 0.1},
            "tracker": {},
        },
        detector=FixtureDetector(),
    )
    with pytest.raises(LabError):
        pipeline.run(BrokenSource(iter([0])))
    assert pipeline.tracker._closed and not pipeline.tracker._tracks


def test_recovery_proposal_is_not_published_as_high_score_detection(make_pipeline):
    class LowThird(FixtureDetector):
        def detect(self, image, identity):
            score = 0.15 if identity.observation_ns == 200_000_000 else 0.9
            return DetectionBatch(
                identity,
                (Detection(0, "person", ObjectClass.PERSON, score, Box(1, 1, 3, 4)),),
                self.provenance,
                image.mapping.fingerprint,
                0,
                0,
            )

    pipeline, recorder = make_pipeline(
        {
            "record_session": True,
            "intervals_ns": {"detector": 100_000_000},
            "detector": {"weights": "unused.pt", "sha256": "a" * 64, "confidence": 0.1},
            "tracker": {"minimum_hits": 2},
        },
        detector=LowThird(),
    )
    pipeline.run(SyntheticSource(iter([0, 100_000_000, 200_000_000])))
    frames = [r for r in records(recorder) if r["type"] == "frame_result"]
    assert frames[-1]["detector"]["detections"] == []
    assert frames[-1]["tracks"]["detector_evidence"] == "SUCCESS"
    assert frames[-1]["tracks"]["tracks"][0]["observation_status"] == "OBSERVED"
    assert frames[-1]["tracks"]["tracks"][0]["observation_confidence"] == 0.15


def test_tracker_close_failure_still_finalizes_recording(make_pipeline):
    from perception_lab.tracking import AssociationTracker

    pipeline, recorder = make_pipeline(
        {
            "record_session": True,
            "detector": {"weights": "unused.pt", "sha256": "a" * 64, "confidence": 0.1},
            "tracker": {},
        },
        detector=FixtureDetector(),
    )

    class BrokenClose(AssociationTracker):
        def close(self):
            super().close()
            raise RuntimeError("private cleanup failure")

    pipeline.tracker = BrokenClose(pipeline.config.tracker, recorder.session_id, "synthetic", 8, 6)
    with pytest.raises(LabError, match="TRACKER_CLOSE_FAILED"):
        pipeline.run(SyntheticSource(iter([0])))
    assert recorder.manifest["termination_reason"] == "FATAL"
    assert pipeline.tracker._closed


def test_forward_gap_explicitly_resets_and_retires_old_ids(make_pipeline):
    pipeline, recorder = make_pipeline(
        {
            "record_session": True,
            "detector": {"weights": "unused.pt", "sha256": "a" * 64, "confidence": 0.1},
            "tracker": {"minimum_hits": 2},
        },
        detector=FixtureDetector(),
    )
    pipeline.run(SyntheticSource(iter([0, 100_000_000, 6_000_000_000])))
    frames = [r for r in records(recorder) if r["type"] == "frame_result"]
    old = frames[1]["tracks"]["tracks"][0]["track_id"]
    last = frames[-1]["tracks"]
    assert last["removed"] == [old]
    assert last["tracks"][0]["track_id"]["serial"] > old["serial"]
    assert last["tracks"][0]["lifecycle"] == "TENTATIVE"
    assert "FORWARD_GAP_RESET" in last["diagnostics"]
    assert recorder.manifest["summary"]["tracking_peaks"]["gap_resets"] == 1
    assert pipeline._tracking_ids == ()
