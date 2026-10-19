"""Empirical operating points; never interpolate an achievable deployment threshold."""

from dataclasses import dataclass
from math import isfinite
from typing import Literal


@dataclass(frozen=True)
class OperatingPoint:
    threshold: float
    tp: int
    fp: int
    fn: int
    frames: int

    def __post_init__(self) -> None:
        if not 0 <= self.threshold <= 1 or self.frames <= 0:
            raise ValueError("Invalid threshold or frame denominator")
        if any(type(v) is not int or v < 0 for v in (self.tp, self.fp, self.fn, self.frames)):
            raise ValueError("Counts must be nonnegative integers")

    @property
    def recall(self) -> float | None:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else None

    @property
    def precision(self) -> float | None:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else None

    @property
    def fp100(self) -> float:
        return 100 * self.fp / self.frames


def thresholds(floor: float, step: float = 0.01) -> tuple[float, ...]:
    """Fixed 0.01..0.95 grid, rejecting unsupported ranges rather than inventing scores."""
    if not 0 <= floor <= 0.95 or step != 0.01:
        raise ValueError("Expected a supported floor and 0.01 grid")
    return tuple(i / 100 for i in range(1, 96) if i / 100 >= floor)


def select(
    points: tuple[OperatingPoint, ...],
    kind: Literal["fp100", "precision", "recall"],
    target: float,
) -> OperatingPoint | None:
    """Max recall within FP/precision constraints; min FP at required recall.

    Deterministic ties prefer precision, then higher threshold. All results are
    observed grid points, not an interpolated claim. Zero predictions have unknown
    precision. Empty truth has unknown recall and cannot qualify.
    """
    if not isfinite(target) or target < 0 or (kind != "fp100" and target > 1):
        raise ValueError("Invalid target")
    if kind not in {"fp100", "precision", "recall"}:
        raise ValueError("Unknown constraint")
    if points and len({(p.frames, p.tp + p.fn) for p in points}) != 1:
        raise ValueError("Cannot compare different evaluation denominators")
    candidates = [
        p
        for p in points
        if p.recall is not None
        and (
            (kind == "fp100" and p.fp100 <= target)
            or (kind == "precision" and p.precision is not None and p.precision >= target)
            or (kind == "recall" and p.recall >= target)
        )
    ]
    if not candidates:
        return None
    if kind == "recall":
        return min(candidates, key=lambda p: (p.fp100, -(p.recall or 0), -p.threshold))
    return max(candidates, key=lambda p: (p.recall or 0, -p.fp100, p.threshold))


def precision_envelope(points: tuple[OperatingPoint, ...], recall: float) -> float | None:
    """Upper precision envelope for plotting only; no extrapolation past observed recall."""
    if not 0 <= recall <= 1:
        raise ValueError("Invalid recall")
    values = [
        p.precision
        for p in points
        if p.recall is not None and p.recall >= recall and p.precision is not None
    ]
    return max(values) if values else None


def pareto_3d(values: dict[str, tuple[float, float, float]]) -> tuple[str, ...]:
    """Recall (maximize), FP/100 and latency (minimize). Licensing is separate."""
    if any(
        not all(isfinite(v) for v in row) or not 0 <= row[0] <= 1 or min(row[1:]) < 0
        for row in values.values()
    ):
        raise ValueError("Invalid Pareto metric")
    return tuple(
        name
        for name, row in sorted(values.items())
        if not any(
            other[0] >= row[0] and other[1] <= row[1] and other[2] <= row[2] and other != row
            for other in values.values()
        )
    )
