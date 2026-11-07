"""Bounded convex point-path geometry; distances are in the supplied plane's units."""

from math import hypot, isfinite

from .corridor import image_distance
from .corridor_types import Point2
from .trajectory_corridor import entry_fraction


def validate_polygon(polygon: tuple[Point2, ...]) -> None:
    if not 3 <= len(polygon) <= 16 or any(
        len(p) != 2 or any(not isfinite(v) or abs(v) > 1e9 for v in p) for p in polygon
    ):
        raise ValueError("Finite bounded convex polygon required")
    area = sum(
        a[0] * polygon[(i + 1) % len(polygon)][1] - a[1] * polygon[(i + 1) % len(polygon)][0]
        for i, a in enumerate(polygon)
    )
    if abs(area) < 1e-9:
        raise ValueError("Degenerate polygon")
    sign = 1 if area > 0 else -1
    for i, a in enumerate(polygon):
        b = polygon[(i + 1) % len(polygon)]
        if hypot(b[0] - a[0], b[1] - a[1]) <= 1e-9:
            raise ValueError("Duplicate polygon vertex")
        if any(
            sign * ((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])) < -1e-9
            for p in polygon
        ):
            raise ValueError("Non-convex or self-crossing polygon")


def project(point: Point2, a: Point2, b: Point2) -> tuple[float, float]:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = dx * dx + dy * dy
    fraction = (
        max(0.0, min(1.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length))
        if length
        else 0.0
    )
    return hypot(point[0] - a[0] - fraction * dx, point[1] - a[1] - fraction * dy), fraction


def segment(
    a: Point2, b: Point2, polygon: tuple[Point2, ...]
) -> tuple[tuple[float, float] | None, float, float]:
    """Intersection interval, minimum distance, and first minimizer fraction."""
    if a == b:
        distance = image_distance(a, polygon)
        return ((0.0, 1.0), 0.0, 0.0) if distance <= 0 else (None, distance, 0.0)
    entry = entry_fraction(a, b, polygon)
    if entry is not None:
        reverse = entry_fraction(b, a, polygon)
        assert reverse is not None
        return (entry, 1.0 - reverse), 0.0, entry
    best = (float("inf"), 0.0)
    for i, p in enumerate(polygon):
        q = polygon[(i + 1) % len(polygon)]
        candidates = (
            project(p, a, b),
            project(q, a, b),
            (project(a, p, q)[0], 0.0),
            (project(b, p, q)[0], 1.0),
        )
        best = min(best, *candidates)
    return None, *best


def unsigned_distance(point: Point2, polygon: tuple[Point2, ...]) -> float:
    return max(0.0, image_distance(point, polygon))
