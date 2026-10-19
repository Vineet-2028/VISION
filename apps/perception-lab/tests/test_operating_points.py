import pytest

from perception_lab.operating_points import (
    OperatingPoint as P,
)
from perception_lab.operating_points import (
    pareto_3d,
    precision_envelope,
    select,
    thresholds,
)


def test_fixed_fp_uses_frame_denominator_and_maximum_recall():
    points = (P(0.1, 9, 3, 1, 4), P(0.4, 8, 2, 2, 4), P(0.8, 5, 0, 5, 4))
    assert select(points, "fp100", 50) == points[1]
    assert select(points, "fp100", 25) == points[2]
    assert select(points, "recall", 0.9) == points[0]
    assert select(points, "recall", 0.95) is None
    assert select(points, "precision", 0.9) == points[2]


def test_no_predictions_does_not_mean_perfect_precision():
    assert select((P(0.95, 0, 0, 10, 4),), "precision", 0.8) is None
    assert select((P(0.95, 0, 0, 0, 4),), "fp100", 25) is None


def test_grid_cannot_recover_predictions_below_floor():
    assert thresholds(0.05) == tuple(i / 100 for i in range(5, 96))
    assert len(thresholds(0.01)) == 95
    with pytest.raises(ValueError):
        thresholds(float("nan"))


def test_precision_envelope_never_extrapolates_unreachable_recall():
    points = (P(0.2, 8, 4, 2, 10), P(0.5, 5, 0, 5, 10))
    assert precision_envelope(points, 0.5) == 1
    assert precision_envelope(points, 0.8) == 2 / 3
    assert precision_envelope(points, 0.81) is None


def test_operating_points_require_same_dataset_denominators():
    with pytest.raises(ValueError):
        select((P(0.1, 1, 0, 0, 1), P(0.2, 1, 0, 1, 1)), "fp100", 25)


def test_pareto_uses_all_three_dimensions_and_retains_equal_points():
    assert pareto_3d(
        {"a": (0.8, 20, 100), "b": (0.7, 20, 100), "c": (0.9, 100, 200), "d": (0.8, 20, 100)}
    ) == ("a", "c", "d")
