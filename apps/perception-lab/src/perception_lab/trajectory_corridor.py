"""Analytic point-path entry against a frozen image corridor, not collision time."""

from math import isfinite

from .corridor import image_distance
from .corridor_types import CorridorAnalysis
from .trajectory_types import PredictedTrajectory, TrajectoryCorridorRelation, TrajectoryDomain


def entry_fraction(
    a: tuple[float, float], b: tuple[float, float], polygon: tuple[tuple[float, float], ...]
) -> float | None:
    """Clip a segment against a convex polygon; handles entry between sample horizons."""
    if len(polygon) < 3 or len(polygon) > 16 or not all(isfinite(x) for p in polygon for x in p):
        return None
    area = sum(
        p[0] * polygon[(i + 1) % len(polygon)][1] - p[1] * polygon[(i + 1) % len(polygon)][0]
        for i, p in enumerate(polygon)
    )
    if abs(area) < 1e-12:
        return None
    sign, lower, upper = (1 if area > 0 else -1), 0.0, 1.0
    for i, p in enumerate(polygon):
        q = polygon[(i + 1) % len(polygon)]
        dx, dy = q[0] - p[0], q[1] - p[1]
        start = sign * (dx * (a[1] - p[1]) - dy * (a[0] - p[0]))
        delta = sign * (dx * (b[1] - a[1]) - dy * (b[0] - a[0]))
        if abs(delta) < 1e-12:
            if start < 0:
                return None
        elif delta > 0:
            lower = max(lower, -start / delta)
        else:
            upper = min(upper, -start / delta)
        if lower > upper:
            return None
    return lower


def relate(t: PredictedTrajectory, analysis: CorridorAnalysis) -> TrajectoryCorridorRelation:
    polygon = analysis.corridor.image_polygon
    if (
        t.coordinate_space != TrajectoryDomain.IMAGE
        or t.motion_basis != "OBSERVED_HISTORY"
        or len(polygon) < 3
        or analysis.corridor.quality == "UNAVAILABLE"
    ):
        return TrajectoryCorridorRelation(
            t.entity_id,
            t.trajectory_id,
            "UNKNOWN",
            (),
            None,
            "UNAVAILABLE",
            "UNAVAILABLE_COORDINATE_MAPPING",
        )

    def relation(point: tuple[float, ...]) -> str:
        return (
            "PREDICTED_INSIDE_CORRIDOR"
            if image_distance((point[0], point[1]), polygon) <= 0
            else "PREDICTED_OUTSIDE"
        )

    current = relation(t.origin)
    future = tuple((s.horizon_ns, relation(s.position)) for s in t.samples)
    entry_time = None
    previous, previous_horizon = t.origin, 0
    for sample in t.samples:
        if sample.horizon_ns <= previous_horizon:
            raise ValueError("Increasing trajectory horizons required")
        entry = entry_fraction(
            (previous[0], previous[1]), (sample.position[0], sample.position[1]), polygon
        )
        if entry is not None:
            entry_time = previous_horizon + round(entry * (sample.horizon_ns - previous_horizon))
            break
        previous, previous_horizon = sample.position, sample.horizon_ns
    return TrajectoryCorridorRelation(
        t.entity_id,
        t.trajectory_id,
        current,
        future,
        entry_time,
        t.quality,
        "IMAGE_SPACE_FROZEN_POLYGON",
    )
