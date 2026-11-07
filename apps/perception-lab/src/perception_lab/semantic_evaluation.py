"""Ignore-aware reviewed-mask metrics; draft proposals cannot qualify a model."""

import cv2
import numpy as np
from numpy.typing import NDArray

from .semantics import IGNORE
from .semantics import SemanticClass as C
from .surfaces import boundaries


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def evaluate_masks(
    predicted: NDArray[np.uint8], truth: NDArray[np.uint8], *, review_status: str
) -> dict[str, object]:
    if review_status != "HUMAN_REVIEWED":
        raise ValueError("Human-reviewed segmentation truth required")
    if (
        predicted.dtype != np.uint8
        or truth.dtype != np.uint8
        or predicted.ndim != 2
        or predicted.shape != truth.shape
        or predicted.size > 8_294_400
        or np.any(predicted >= len(C))
        or np.any((truth >= len(C)) & (truth != IGNORE))
    ):
        raise ValueError("Invalid semantic evaluation masks")
    valid = truth != IGNORE
    if not valid.any():
        raise ValueError("No reviewed pixels")
    matrix = np.bincount(
        truth[valid].astype(np.int64) * len(C) + predicted[valid], minlength=len(C) ** 2
    ).reshape(len(C), len(C))
    rows: dict[str, object] = {}
    ious: list[float] = []
    for label in C:
        tp = int(matrix[label, label])
        actual, proposed = int(matrix[label].sum()), int(matrix[:, label].sum())
        iou = ratio(tp, actual + proposed - tp)
        if iou is not None:
            ious.append(iou)
        rows[label.name] = {
            "truth_pixels": actual,
            "predicted_pixels": proposed,
            "iou": iou,
            "precision": ratio(tp, proposed),
            "recall": ratio(tp, actual),
            "dice": ratio(2 * tp, actual + proposed),
        }
    potential = np.isin(predicted, [C.SIDEWALK, C.PATH, C.FLOOR]) & valid
    true_potential = np.isin(truth, [C.SIDEWALK, C.PATH, C.FLOOR]) & valid
    # Strict semantic-evidence error, not a safety-risk probability. ROAD remains contextual.
    false = potential & ~true_potential
    obstacles = np.isin(
        truth,
        [
            C.WALL,
            C.BUILDING,
            C.STAIRS,
            C.CURB,
            C.PERSON,
            C.VEHICLE,
            C.BICYCLE,
            C.MOTORCYCLE,
            C.POLE,
            C.FENCE,
            C.OBJECT_OTHER,
            C.VEGETATION,
        ],
    )
    # Erode reviewed support so ignore borders cannot fabricate/match a class boundary.
    interior = cv2.erode(valid.astype(np.uint8), np.ones((3, 3), np.uint8)) != 0
    pb, tb = boundaries(predicted) & interior, boundaries(truth) & interior
    near_p = cv2.dilate(pb.astype(np.uint8), np.ones((3, 3), np.uint8)) != 0
    near_t = cv2.dilate(tb.astype(np.uint8), np.ones((3, 3), np.uint8)) != 0
    has_boundary = bool(pb.any() or tb.any())
    precision = ratio(int((pb & near_t).sum()), int(pb.sum()))
    recall = ratio(int((tb & near_p).sum()), int(tb.sum()))
    if has_boundary:
        precision = precision if precision is not None else 0.0
        recall = recall if recall is not None else 0.0
    fscore = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else (0.0 if has_boundary else None)
    )
    ground_classes = [C.SIDEWALK, C.ROAD, C.PATH, C.FLOOR, C.GROUND_OTHER, C.GRASS]
    tg = np.isin(truth, ground_classes) & valid
    pg = np.isin(predicted, ground_classes)
    bottom = slice(truth.shape[0] * 3 // 4, truth.shape[0])
    return {
        "reviewed_pixels": int(valid.sum()),
        "confusion_matrix": matrix.tolist(),
        "classes": rows,
        "miou": float(np.mean(ious)) if ious else None,
        "pixel_accuracy": float((predicted[valid] == truth[valid]).mean()),
        "unknown_fraction": float((predicted[valid] == C.UNKNOWN).mean()),
        "potential_precision": ratio(int((potential & true_potential).sum()), int(potential.sum())),
        "potential_recall": ratio(
            int((potential & true_potential).sum()), int(true_potential.sum())
        ),
        "false_traversable_pixels": int(false.sum()),
        "false_traversable_fraction_of_proposals": ratio(int(false.sum()), int(potential.sum())),
        "obstacle_as_traversable_pixels": int((potential & obstacles).sum()),
        "ground_recall": ratio(int((pg & tg).sum()), int(tg.sum())),
        "bottom_ground_recall": ratio(int((pg[bottom] & tg[bottom]).sum()), int(tg[bottom].sum())),
        "boundary_precision_1px": precision,
        "boundary_recall_1px": recall,
        "boundary_f1_1px": fscore,
    }


def decode_runs(runs: list[list[int]], width: int, height: int) -> NDArray[np.uint8]:
    if not 0 < width * height <= 8_294_400 or len(runs) > width * height:
        raise ValueError("Annotation exceeds bounds")
    result = np.empty(width * height, dtype=np.uint8)
    offset = 0
    for run in runs:
        if (
            len(run) != 2
            or any(type(v) is not int for v in run)
            or run[0] not in {*range(len(C)), IGNORE}
            or run[1] <= 0
            or offset + run[1] > result.size
        ):
            raise ValueError("Invalid annotation RLE")
        result[offset : offset + run[1]] = run[0]
        offset += run[1]
    if offset != result.size:
        raise ValueError("Incomplete annotation RLE")
    return result.reshape(height, width)
