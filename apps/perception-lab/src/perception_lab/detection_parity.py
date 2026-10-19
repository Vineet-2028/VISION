"""Detection-level parity diagnostics, separate from ground-truth accuracy."""

from dataclasses import dataclass

from .detection import Detection
from .detection_metrics import iou


@dataclass(frozen=True)
class Parity:
    matched: int
    missing: int
    extra: int
    outside_tolerance: int
    max_score_error: float
    max_box_error_pixels: float

    @property
    def passed(self) -> bool:
        return self.missing == self.extra == self.outside_tolerance == 0


def compare(
    reference: tuple[Detection, ...],
    candidate: tuple[Detection, ...],
    *,
    score_tolerance: float = 0.001,
    box_tolerance_pixels: float = 0.5,
) -> Parity:
    """Greedy same-class IoU association; every unmatched detection fails strict parity.

    Tolerances apply to scores and each original-image box edge. Matching uses IoU>=.5
    only for association, never as a substitute for the stricter edge tolerance.
    """
    from math import isfinite

    if any(not isfinite(v) or v < 0 for v in (score_tolerance, box_tolerance_pixels)):
        raise ValueError("Invalid parity tolerance")
    remaining = set(range(len(candidate)))
    matched = bad = 0
    max_score = max_box = 0.0
    for item in sorted(reference, key=lambda p: -p.confidence):
        options = [
            (iou(item.box, candidate[i].box), i)
            for i in sorted(remaining)
            if item.class_id == candidate[i].class_id and item.class_name == candidate[i].class_name
        ]
        overlap, index = max(options, default=(0.0, -1), key=lambda pair: (pair[0], -pair[1]))
        if overlap < 0.5:
            continue
        remaining.remove(index)
        other = candidate[index]
        score = abs(item.confidence - other.confidence)
        edge = max(
            abs(getattr(item.box, field) - getattr(other.box, field))
            for field in ("x1", "y1", "x2", "y2")
        )
        matched += 1
        bad += int(score > score_tolerance or edge > box_tolerance_pixels)
        max_score, max_box = max(max_score, score), max(max_box, edge)
    return Parity(matched, len(reference) - matched, len(remaining), bad, max_score, max_box)
