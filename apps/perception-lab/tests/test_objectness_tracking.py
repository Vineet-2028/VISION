from perception_lab.contracts import ComponentProvenance, FrameIdentity, TimingProvenance
from perception_lab.detection import Box, Detection, DetectionBatch, ObjectClass
from perception_lab.tracking import AssociationTracker
from perception_lab.tracking_config import TrackerConfig
from perception_lab.tracking_types import DetectorEvidence


def step(tracker, sequence, labels):
    identity = FrameIdentity("source", sequence, sequence * 100_000_000, TimingProvenance.SYNTHETIC)
    detections = tuple(
        Detection(
            i,
            label,
            ObjectClass.PERSON if label == "person" else ObjectClass.UNKNOWN,
            0.9,
            Box(10, 10, 30, 50),
        )
        for i, label in enumerate(labels)
    )
    return tracker.update(
        "session",
        identity,
        DetectorEvidence.SUCCESS,
        DetectionBatch(
            identity, detections, ComponentProvenance("fixture", "detector"), "a" * 64, 0, 0
        ),
    )


def test_unknown_region_survives_tracking_and_semantic_name_changes():
    tracker = AssociationTracker(
        TrackerConfig(), "session", "source", 640, 480, objectness_first=True
    )
    ids = [
        step(tracker, i, [label]).tracks[0].track_id
        for i, label in enumerate(["chair", "furniture", "person", "unrecognized"])
    ]
    assert len(set(ids)) == 1
    assert tracker.provenance.model_id == "image-space-objectness-v02"


def test_semantically_different_duplicate_boxes_do_not_spawn_extra_tracks():
    tracker = AssociationTracker(
        TrackerConfig(), "session", "source", 640, 480, objectness_first=True
    )
    assert len(step(tracker, 0, ["chair", "person", "unknown"]).tracks) == 1


def test_frozen_v0_mode_keeps_its_original_unknown_admission_policy():
    tracker = AssociationTracker(TrackerConfig(), "session", "source", 640, 480)
    assert step(tracker, 0, ["chair"]).tracks == ()
    assert tracker.provenance.model_id == "image-space-v1"
