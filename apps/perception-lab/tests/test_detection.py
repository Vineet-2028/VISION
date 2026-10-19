import math

import pytest

from perception_lab.components import NoOpDetector, SegmentationOutput
from perception_lab.contracts import LabError
from perception_lab.detection import Box, Detection, ObjectClass, ObjectGroup, group, semantic_class
from perception_lab.detection_metrics import (
    CandidateScore,
    GroundTruth,
    SelectionPolicy,
    evaluate,
    iou,
    localization_error,
    pareto_front,
    size_class,
)
from perception_lab.sources import SyntheticSource


def detection(box=None, confidence=0.9, label=ObjectClass.PERSON):
    return Detection(0, label.value.lower(), label, confidence, box or Box(0, 0, 10, 10))


def test_iou_hand_computed():
    assert iou(Box(0, 0, 2, 2), Box(1, 0, 3, 2)) == pytest.approx(1 / 3)
    assert iou(Box(0, 0, 0, 0), Box(0, 0, 0, 0)) == 0
    assert iou(Box(0, 0, 1, 1), Box(1, 0, 2, 1)) == 0


def test_matching_confidence_order_duplicates_wrong_class_and_counts():
    truth = (
        GroundTruth(ObjectClass.PERSON, Box(0, 0, 10, 10)),
        GroundTruth(ObjectClass.DOG, Box(20, 20, 30, 30)),
    )
    result = evaluate(
        (detection(confidence=0.6), detection(), detection(label=ObjectClass.CAR)), truth
    )
    assert (result.counts.tp, result.counts.fp, result.counts.fn) == (1, 2, 1)
    assert result.matches[0].prediction == 1
    assert result.counts.precision == pytest.approx(1 / 3)
    assert result.counts.recall == 0.5
    assert result.counts.f1 == 0.4


def test_ignore_prefers_regular_gt_and_crowd_absorbs_multiple():
    box = Box(0, 0, 10, 10)
    result = evaluate(
        (detection(), detection(), detection()),
        (GroundTruth(ObjectClass.PERSON, box, crowd=True), GroundTruth(ObjectClass.PERSON, box)),
    )
    assert result.counts.tp == 1 and result.counts.fp == result.counts.fn == 0
    assert result.matches[0].truth == 1
    assert result.ignored_predictions == (1, 2)


def test_non_crowd_ignore_absorbs_only_one():
    result = evaluate(
        (detection(), detection()),
        (GroundTruth(ObjectClass.PERSON, Box(0, 0, 10, 10), ignore=True),),
    )
    assert result.counts.fp == 1 and result.counts.fn == 0


def test_confidence_and_iou_thresholds_are_inclusive():
    gt = (GroundTruth(ObjectClass.PERSON, Box(0, 0, 10, 10)),)
    prediction = (detection(Box(0, 0, 5, 10), confidence=0.5),)
    assert evaluate(prediction, gt, 0.5, 0.5).counts.tp == 1
    assert evaluate(prediction, gt, 0.51).counts.fn == 1
    assert evaluate(prediction, gt, overlap=0.75).counts.fp == 1
    assert evaluate((), ()).counts.recall is None


@pytest.mark.parametrize("value", [math.nan, math.inf, -0.1, 1.1])
def test_invalid_confidences_rejected(value):
    with pytest.raises(ValueError):
        detection(confidence=value)
    with pytest.raises(ValueError):
        evaluate((), (), confidence=value)


def test_sizes_and_bottom_center_have_exact_boundaries():
    assert size_class(Box(0, 0, 1, 1), 100, 100) == "TINY"
    assert size_class(Box(0, 0, 10, 1), 100, 100) == "SMALL"
    assert size_class(Box(0, 0, 10, 10), 100, 100) == "MEDIUM"
    assert size_class(Box(0, 0, 100, 10), 100, 100) == "LARGE"
    center, bottom = localization_error(Box(0, 0, 10, 20), Box(0, 0, 10, 10), 100, 100)
    assert center == 0.05 and bottom == 0.1


def test_pareto_and_hard_license_gate():
    fast = CandidateScore("fast", 0.7, 10, 1, True, True)
    accurate = CandidateScore("accurate", 0.9, 20, 1, True, False)
    dominated = CandidateScore("dominated", 0.6, 30, 1, True, True)
    assert pareto_front((fast, accurate, dominated)) == (fast, accurate)
    policy = SelectionPolicy(0.65, 25, 2)
    assert policy.accepts(fast) and not policy.accepts(accurate)
    assert not policy.accepts(dominated)


def test_taxonomy_does_not_invent_riders():
    assert semantic_class("bicycle") == ObjectClass.BICYCLE
    assert semantic_class("pole") == ObjectClass.UNKNOWN
    assert group(ObjectClass.BICYCLE) == ObjectGroup.VEHICLE


@pytest.mark.parametrize(
    "operation,width,height,left,top,expected",
    [
        ("resize", 16, 12, 0, 0, (1, 1, 3, 3)),
        ("crop", 4, 4, 2, 1, (4, 3, 8, 7)),
        ("letterbox", 16, 16, 0, 2, (1, 0, 3, 2)),
    ],
)
def test_restoration_uses_actual_core_transform(
    geometry, operation, width, height, left, top, expected
):
    mapping = geometry.mapping(operation, width, height, left, top, (16, 12))
    assert mapping.restore_box(Box(2, 2, 6, 6)).coordinates == pytest.approx(expected)
    assert len(mapping.fingerprint) == 64


def test_pipeline_rejects_wrong_component_output_type(make_pipeline):
    class WrongDetector(NoOpDetector):
        def detect(self, image, identity):
            return SegmentationOutput(identity, "not a detection")

    pipeline, recorder = make_pipeline(detector=WrongDetector())
    with pytest.raises(LabError):
        pipeline.run(SyntheticSource(iter([0])))
    assert recorder.manifest["termination_reason"] == "FATAL"
    assert pipeline.metrics.counts["processed"] == 0


def test_model_letterbox_uses_actual_rounded_axis_scales(geometry):
    mapping = geometry.mapping("identity", 8, 6, 0, 0, (8, 6))
    model, layout = mapping.letterboxed(15, 15)
    assert layout == (15, 11, 0, 2)
    assert model.restore_box(Box(0, 2, 15, 13)).coordinates == pytest.approx((0, 0, 8, 6))


def test_verified_occlusion_state_cannot_conflict_with_boolean_annotation():
    with pytest.raises(ValueError, match="Conflicting"):
        GroundTruth(
            ObjectClass.PERSON,
            Box(0, 0, 10, 10),
            occluded=False,
            occlusion_state="HEAVILY_OCCLUDED",
        )
    assert GroundTruth(ObjectClass.PERSON, Box(0, 0, 10, 10)).occlusion_state == "UNKNOWN"
