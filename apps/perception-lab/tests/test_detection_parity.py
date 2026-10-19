from dataclasses import replace

from perception_lab.detection import Box, Detection, ObjectClass
from perception_lab.detection_parity import compare


def test_parity_associates_reordered_boxes_and_applies_edge_and_score_tolerances():
    a = Detection(0, "person", ObjectClass.PERSON, 0.8, Box(0, 0, 10, 10))
    b = replace(a, box=Box(20, 20, 30, 30))
    result = compare((a, b), (b, replace(a, confidence=0.8005, box=Box(0.1, 0, 10, 10))))
    assert result.passed and result.matched == 2
    assert result.max_box_error_pixels == 0.1
    assert not compare((a,), (replace(a, box=Box(0.6, 0, 10, 10)),)).passed
    assert not compare((a,), (replace(a, confidence=0.81),)).passed


def test_parity_never_hides_missing_extra_or_wrong_class_predictions():
    a = Detection(0, "person", ObjectClass.PERSON, 0.8, Box(0, 0, 10, 10))
    b = Detection(2, "car", ObjectClass.CAR, 0.8, a.box)
    result = compare((a,), (b,))
    assert result.missing == result.extra == 1
    assert not result.passed
    assert compare((a,), (a, a)).extra == 1
