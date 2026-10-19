from dataclasses import asdict, replace
from itertools import permutations
from math import inf

import numpy as np
import pytest

from perception_lab.contracts import ComponentProvenance, FrameIdentity, TimingProvenance
from perception_lab.detection import Box, Detection, DetectionBatch, ObjectClass
from perception_lab.tracking import AssociationTracker
from perception_lab.tracking_assignment import assign
from perception_lab.tracking_config import TrackerConfig
from perception_lab.tracking_motion import ImageMotion
from perception_lab.tracking_types import DetectorEvidence as E
from perception_lab.tracking_types import Lifecycle

P = ComponentProvenance("fixture", "detector")


def identity(ms, sequence=None):
    return FrameIdentity(
        "clock", ms if sequence is None else sequence, ms * 1_000_000, TimingProvenance.SYNTHETIC
    )


def detection(x=10, label="PERSON", confidence=0.9):
    return Detection(0, label.lower(), ObjectClass(label), confidence, Box(x, 10, x + 20, 50))


def tracker(**kwargs):
    return AssociationTracker(TrackerConfig(minimum_hits=2, **kwargs), "session", "clock", 640, 480)


def update(t, ms, detections=None, evidence=None):
    frame = identity(ms)
    batch = (
        None if detections is None else DetectionBatch(frame, tuple(detections), P, "a" * 64, 0, 0)
    )
    evidence = evidence or (
        E.NO_DETECTOR_RUN if batch is None else E.SUCCESS if detections else E.SUCCESS_EMPTY
    )
    return t.update(
        "session", frame, evidence, batch, "INFERENCE_FAILURE" if evidence == E.FAILURE else None
    )


@pytest.mark.parametrize("kind", ["iou", "motion", "two_stage"])
def test_identity_confirmation_prediction_reassociation(kind):
    t = tracker(tracker_type=kind)
    first = update(t, 0, [detection()]).tracks[0]
    second = update(t, 100, [detection(11)]).tracks[0]
    predicted = update(t, 150).tracks[0]
    final = update(t, 200, [detection(12)]).tracks[0]
    assert first.lifecycle == Lifecycle.TENTATIVE
    assert second.lifecycle == Lifecycle.CONFIRMED
    assert predicted.observation_status == "PREDICTED"
    assert predicted.latest_observed_ns == 100_000_000
    assert predicted.misses == 0
    assert first.track_id == second.track_id == predicted.track_id == final.track_id
    assert final.observation_status == "OBSERVED"


def test_empty_failure_and_unscheduled_have_different_semantics():
    t = tracker()
    update(t, 0, [detection()])
    confirmed = update(t, 100, [detection()]).tracks[0]
    absent = update(t, 150).tracks[0]
    failure = update(t, 200, evidence=E.FAILURE).tracks[0]
    empty = update(t, 250, []).tracks[0]
    assert absent.misses == failure.misses == 0
    assert empty.misses == 1 and empty.lifecycle == Lifecycle.LOST
    assert failure.latest_failure == "INFERENCE_FAILURE"
    assert confirmed.quality > absent.quality > failure.quality
    assert absent.uncertainty_proxy <= failure.uncertainty_proxy


def test_short_gap_recovers_but_long_gap_retires_identity():
    t = tracker()
    old = update(t, 0, [detection()]).tracks[0].track_id
    update(t, 100, [detection()])
    update(t, 200, [])
    update(t, 300, [])
    assert update(t, 400, [detection()]).tracks[0].track_id == old
    expired = update(t, 1500, [detection()])
    assert expired.removed == (old,)
    assert expired.tracks[0].track_id != old


def test_low_confidence_recovers_only_confirmed_never_births():
    t = tracker()
    assert not update(t, 0, [detection(confidence=0.15)]).tracks
    old = update(t, 100, [detection()]).tracks[0].track_id
    update(t, 200, [detection()])
    recovered = update(t, 300, [detection(confidence=0.15)])
    assert recovered.tracks[0].track_id == old
    assert recovered.tracks[0].observation_status == "OBSERVED"
    single = tracker(tracker_type="motion")
    update(single, 0, [detection()])
    update(single, 100, [detection()])
    assert (
        update(single, 200, [detection(confidence=0.15)]).tracks[0].observation_status
        == "PREDICTED"
    )


def test_category_flicker_stabilizes_but_can_change():
    t = tracker()
    labels = ["BICYCLE", "BICYCLE", "MOTORCYCLE", "BICYCLE"]
    outputs = [
        update(t, i * 100, [detection(label=label)]).tracks[0] for i, label in enumerate(labels)
    ]
    assert all(s.category == ObjectClass.BICYCLE for s in outputs)
    for i in range(4, 14):
        last = update(t, i * 100, [detection(label="MOTORCYCLE")]).tracks[0]
    assert last.category == ObjectClass.MOTORCYCLE


@pytest.mark.parametrize("model", ["alpha_beta", "kalman"])
def test_variable_dt_prediction_and_positive_covariance(model):
    t = tracker(tracker_type="motion", motion_model=model)
    for ms in [0, 31, 72, 105, 190]:
        observed = update(t, ms, [detection(10 + ms / 100)]).tracks[0]
    future = update(t, 290).tracks[0]
    assert future.bbox.x1 - observed.bbox.x1 == pytest.approx(
        observed.image_velocity_pixels_per_second[0] * 0.1
    )
    assert future.uncertainty_proxy >= observed.uncertainty_proxy
    state = t._tracks[0].motion
    assert np.linalg.eigvalsh(state.covariance).min() >= -1e-9


@pytest.mark.parametrize("bad", ["clock", "session", "backward", "sequence", "large_gap", "batch"])
def test_incompatible_update_rejects_without_state_mutation(bad):
    t = tracker()
    update(t, 100, [detection()])
    before = asdict(update(t, 200, [detection()]))
    frame, session = identity(300), "session"
    if bad == "clock":
        frame = replace(frame, source_id="other")
    if bad == "session":
        session = "other"
    if bad == "backward":
        frame = identity(199)
    if bad == "sequence":
        frame = identity(300, 100)
    if bad == "large_gap":
        frame = identity(6000)
    batch = DetectionBatch(identity(301), (), P, "a" * 64, 0, 0) if bad == "batch" else None
    with pytest.raises(ValueError):
        t.update(session, frame, E.NO_DETECTOR_RUN, batch)
    assert t._last == identity(200)
    assert t._tracks[0].hits == before["tracks"][0]["hits"]
    assert update(t, 300, [detection()]).tracks[0].hits == 3


def test_reset_and_close_do_not_reuse_ids():
    t = tracker()
    old = update(t, 0, [detection()]).tracks[0].track_id
    t.close()
    with pytest.raises(ValueError):
        update(t, 100)
    t.reset("session", "clock", 640, 480)
    assert update(t, 0, [detection()]).tracks[0].track_id.serial > old.serial


def test_bounded_tracks_histories_and_deterministic_overload():
    t = tracker(max_tracks=3, max_detections=5, history_capacity=4)
    boxes = [detection(i * 40) for i in range(100)]
    first = update(t, 0, boxes)
    assert len(first.tracks) == 3
    assert set(first.diagnostics) == {"TRACK_CAP_REACHED", "DETECTION_CAP_REACHED"}
    for i in range(1, 1001):
        last = update(t, i * 10, boxes[:3])
    assert len(last.tracks) == 3
    assert all(len(s.history) == 4 for s in last.tracks)
    assert [s.track_id for s in last.tracks] == [s.track_id for s in first.tracks]


def test_duplicate_suppression_is_conservative():
    t = tracker()
    result = update(t, 0, [detection(), detection(), detection(20)])
    assert len(result.tracks) == 2
    assert "DUPLICATE_DETECTION_SUPPRESSED" in result.diagnostics


def test_crossing_same_class_and_detection_order_invariance():
    def replay(reverse):
        t = tracker(tracker_type="motion", alpha=1.0, beta=1.0)
        records = []
        for i in range(8):
            boxes = [detection(10 + i * 10), detection(85 - i * 10)]
            records.append(update(t, i * 100, list(reversed(boxes)) if reverse else boxes))
        return records

    a, b = replay(False), replay(True)
    assert a == b
    assert a[-1].tracks[0].bbox.x1 > a[-1].tracks[1].bbox.x1
    assert len({s.track_id for r in a for s in r.tracks}) == 2


def test_assignment_global_optimum_and_forbidden_edges():
    matrix = [[0.2, 0.3, inf], [0.21, 0.9, 0.4], [0.8, 0.2, 0.1]]
    matched = assign(matrix, 1.3)
    cost = sum(matrix[i][j] for i, j in matched)
    brute = min(sum(matrix[i][j] for i, j in enumerate(p)) for p in permutations(range(3)))
    assert cost == pytest.approx(brute)
    assert assign([[inf], [0.1]], 1.0) == ((1, 0),)
    assert assign([[], []], 1.0) == ()


def test_single_false_detection_expires_unconfirmed_and_snapshots_immutable():
    t = tracker()
    first = update(t, 0, [detection()])
    update(t, 100, [])
    assert not update(t, 1100).tracks
    assert first.tracks[0].hits == 1 and len(first.tracks[0].history) == 1


def test_motion_invalid_size_is_not_silently_clamped():
    m = ImageMotion(Box(0, 0, 1, 1), TrackerConfig())
    m.velocity[2] = -10
    with pytest.raises(ValueError):
        m.predict(1.0)


def test_unmapped_detector_categories_do_not_start_p0_tracks():
    t = tracker()
    d = Detection(56, "chair", ObjectClass.UNKNOWN, 0.9, Box(10, 10, 20, 30))
    assert not update(t, 0, [d]).tracks


def test_alpha_beta_uncertainty_proxy_remains_positive_semidefinite():
    t = tracker()
    for i in range(100):
        update(t, i * 100, [detection(10 + i * 0.1)])
    assert np.linalg.eigvalsh(t._tracks[0].motion.covariance).min() >= 0


def test_zero_score_proposals_do_not_form_zero_evidence_category_votes():
    t = tracker(publication_threshold=0.0, recovery_threshold=0.0)
    assert not update(t, 0, [detection(confidence=0.0)]).tracks
