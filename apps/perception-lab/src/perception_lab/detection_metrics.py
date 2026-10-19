"""Small, explicit detection diagnostics. This is not the official COCO AP evaluator."""

from dataclasses import dataclass
from math import hypot, isfinite
from typing import Literal

from .detection import Box, Detection, ObjectClass


def iou(left: Box, right: Box) -> float:
    intersection = max(0.0, min(left.x2, right.x2) - max(left.x1, right.x1)) * max(
        0.0, min(left.y2, right.y2) - max(left.y1, right.y1)
    )
    union = left.area + right.area - intersection
    return intersection / union if union > 0 else 0.0


@dataclass(frozen=True)
class GroundTruth:
    label: ObjectClass
    box: Box
    ignore: bool = False
    crowd: bool = False
    occluded: bool | None = None
    truncated: bool | None = None
    difficulty: str = "UNKNOWN"
    occlusion_state: Literal["UNKNOWN", "VISIBLE", "PARTIALLY_OCCLUDED", "HEAVILY_OCCLUDED"] = (
        "UNKNOWN"
    )

    def __post_init__(self) -> None:
        if self.occlusion_state not in {
            "UNKNOWN",
            "VISIBLE",
            "PARTIALLY_OCCLUDED",
            "HEAVILY_OCCLUDED",
        }:
            raise ValueError("Invalid occlusion state")
        if self.occluded is not None and self.occlusion_state != "UNKNOWN":
            if self.occluded != (self.occlusion_state != "VISIBLE"):
                raise ValueError("Conflicting occlusion annotations")


@dataclass(frozen=True)
class Match:
    prediction: int
    truth: int
    overlap: float


@dataclass(frozen=True)
class Counts:
    tp: int
    fp: int
    fn: int

    @property
    def precision(self) -> float | None:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else None

    @property
    def recall(self) -> float | None:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else None

    @property
    def f1(self) -> float | None:
        denominator = 2 * self.tp + self.fp + self.fn
        return 2 * self.tp / denominator if denominator else None


@dataclass(frozen=True)
class Evaluation:
    counts: Counts
    matches: tuple[Match, ...]
    false_positives: tuple[int, ...]
    false_negatives: tuple[int, ...]
    ignored_predictions: tuple[int, ...]


def evaluate(
    predictions: tuple[Detection, ...],
    truth: tuple[GroundTruth, ...],
    confidence: float = 0.25,
    overlap: float = 0.5,
) -> Evaluation:
    """Class-aware confidence-greedy one-to-one matches, stable input-order ties.

    Prefer a regular GT to ignored regions. Ordinary ignored GT absorbs at most one
    prediction; crowds absorb multiple using intersection/prediction area like COCO.
    Ignored/crowd GT never enters recall denominators. Missing annotations are not negatives.
    """
    if not 0 <= confidence <= 1 or not 0 < overlap <= 1:
        raise ValueError("Invalid evaluation threshold")
    remaining = {i for i, item in enumerate(truth) if not item.ignore and not item.crowd}
    ignored_used: set[int] = set()
    matches, false_positives, ignored = [], [], []
    ordered = sorted(
        (i for i, item in enumerate(predictions) if item.confidence >= confidence),
        key=lambda i: (-predictions[i].confidence, i),
    )
    for pi in ordered:
        prediction = predictions[pi]
        options = [
            (iou(prediction.box, truth[ti].box), ti)
            for ti in sorted(remaining)
            if prediction.label == truth[ti].label
        ]
        best = max(options, key=lambda pair: (pair[0], -pair[1]), default=(0.0, -1))
        if best[0] >= overlap:
            matches.append(Match(pi, best[1], best[0]))
            remaining.remove(best[1])
            continue
        absorbed = False
        for ti, item in enumerate(truth):
            if item.label != prediction.label or not (item.ignore or item.crowd):
                continue
            if ti in ignored_used:
                continue
            score = iou(prediction.box, item.box)
            if item.crowd and prediction.box.area > 0:
                intersection = max(
                    0.0, min(prediction.box.x2, item.box.x2) - max(prediction.box.x1, item.box.x1)
                ) * max(
                    0.0, min(prediction.box.y2, item.box.y2) - max(prediction.box.y1, item.box.y1)
                )
                score = intersection / prediction.box.area
            if score >= overlap:
                if not item.crowd:
                    ignored_used.add(ti)
                ignored.append(pi)
                absorbed = True
                break
        if not absorbed:
            false_positives.append(pi)
    return Evaluation(
        Counts(len(matches), len(false_positives), len(remaining)),
        tuple(matches),
        tuple(false_positives),
        tuple(sorted(remaining)),
        tuple(ignored),
    )


def size_class(
    box: Box,
    width: int,
    height: int,
    boundaries: tuple[float, float, float] = (
        0.001,
        0.01,
        0.1,
    ),
) -> str:
    """Unclipped area/image-area proxy; equality belongs to the larger bucket."""
    if width <= 0 or height <= 0 or not 0 < boundaries[0] < boundaries[1] < boundaries[2] <= 1:
        raise ValueError("Invalid size policy")
    ratio = box.area / (width * height)
    return ("TINY", "SMALL", "MEDIUM", "LARGE")[sum(ratio >= b for b in boundaries)]


def localization_error(prediction: Box, truth: Box, width: int, height: int) -> tuple[float, float]:
    """Euclidean center and bottom-center error after normalization by each image axis."""
    if width <= 0 or height <= 0:
        raise ValueError("Invalid image dimensions")
    dx = ((prediction.x1 + prediction.x2) / 2 - (truth.x1 + truth.x2) / 2) / width
    dy = ((prediction.y1 + prediction.y2) / 2 - (truth.y1 + truth.y2) / 2) / height
    return hypot(dx, dy), hypot(dx, (prediction.y2 - truth.y2) / height)


@dataclass(frozen=True)
class CandidateScore:
    name: str
    p0_recall: float
    latency_p95_ms: float
    fp_per_100: float
    export_verified: bool
    license_approved: bool

    def __post_init__(self) -> None:
        if (
            not self.name
            or not 0 <= self.p0_recall <= 1
            or any(not isfinite(v) or v < 0 for v in (self.latency_p95_ms, self.fp_per_100))
        ):
            raise ValueError("Invalid candidate measurements")


@dataclass(frozen=True)
class SelectionPolicy:
    min_recall: float
    max_latency_ms: float
    max_fp_per_100: float

    def __post_init__(self) -> None:
        if not 0 <= self.min_recall <= 1 or any(
            not isfinite(v) or v < 0 for v in (self.max_latency_ms, self.max_fp_per_100)
        ):
            raise ValueError("Invalid selection gates")

    def accepts(self, score: CandidateScore) -> bool:
        return (
            score.license_approved
            and score.export_verified
            and score.p0_recall >= self.min_recall
            and score.latency_p95_ms <= self.max_latency_ms
            and score.fp_per_100 <= self.max_fp_per_100
        )


def pareto_front(scores: tuple[CandidateScore, ...]) -> tuple[CandidateScore, ...]:
    """Accuracy/latency non-dominance only; apply hard gates separately before selection."""
    if len({s.name for s in scores}) != len(scores):
        raise ValueError("Duplicate candidate IDs")
    return tuple(
        s
        for s in scores
        if not any(
            other.p0_recall >= s.p0_recall
            and other.latency_p95_ms <= s.latency_p95_ms
            and (other.p0_recall > s.p0_recall or other.latency_p95_ms < s.latency_p95_ms)
            for other in scores
        )
    )
