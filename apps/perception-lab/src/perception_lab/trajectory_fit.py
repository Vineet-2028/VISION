"""Small bounded, unit-agnostic fits. No category priors or confidence probabilities."""

from dataclasses import dataclass
from math import dist, isfinite
from statistics import median


@dataclass(frozen=True)
class Fit:
    position: tuple[float, ...]
    velocity: tuple[float, ...]
    residual: float
    kept: tuple[int, ...]


def linear_fit(
    times: tuple[float, ...],
    points: tuple[tuple[float, ...], ...],
    floor: float,
    multiplier: float,
    last_two: bool = False,
) -> Fit:
    """Median separated-pair seed then inlier OLS; bounded O(history) seed work."""
    n = len(times)
    if (
        n < 2
        or n > 32
        or len(points) != n
        or any(b <= a for a, b in zip(times, times[1:], strict=False))
    ):
        raise ValueError("Strictly increasing bounded observations required")
    d = len(points[0])
    if (
        d not in (2, 3)
        or any(len(p) != d or not all(isfinite(x) for x in p) for p in points)
        or not all(isfinite(t) for t in times)
    ):
        raise ValueError("Finite consistent points required")
    if last_two:
        v = tuple((points[-1][k] - points[-2][k]) / (times[-1] - times[-2]) for k in range(d))
        if not all(isfinite(x) for x in v):
            raise ValueError("Non-finite fit")
        return Fit(points[-1], v, 0.0, (n - 2, n - 1))
    offset = n // 2
    slopes = tuple(
        median(
            (points[i + offset][k] - points[i][k]) / (times[i + offset] - times[i])
            for i in range(n - offset)
        )
        for k in range(d)
    )
    intercept = tuple(
        median(p[k] - slopes[k] * t for t, p in zip(times, points, strict=True)) for k in range(d)
    )
    errors = tuple(
        dist(p, tuple(intercept[k] + slopes[k] * t for k in range(d)))
        for t, p in zip(times, points, strict=True)
    )
    if not all(isfinite(x) for x in (*slopes, *intercept, *errors)):
        raise ValueError("Non-finite fit")
    threshold = multiplier * max(floor, median(errors))
    kept = tuple(i for i, error in enumerate(errors) if error <= threshold)
    if len(kept) < 2:
        return Fit(points[-1], (0.0,) * d, max(errors), (n - 1,))
    mean_t = sum(times[i] for i in kept) / len(kept)
    means = tuple(sum(points[i][k] for i in kept) / len(kept) for k in range(d))
    denominator = sum((times[i] - mean_t) ** 2 for i in kept)
    v = tuple(
        sum((times[i] - mean_t) * (points[i][k] - means[k]) for i in kept) / denominator
        for k in range(d)
    )
    position = tuple(means[k] + v[k] * (times[-1] - mean_t) for k in range(d))
    residual = max(
        dist(points[i], tuple(means[k] + v[k] * (times[i] - mean_t) for k in range(d)))
        for i in kept
    )
    if not all(isfinite(x) for x in (*v, *position, residual)):
        raise ValueError("Non-finite fit")
    return Fit(position, v, residual, kept)
