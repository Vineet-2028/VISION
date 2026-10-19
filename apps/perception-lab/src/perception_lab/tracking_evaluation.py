"""Explicit IoU matching and identity counts, not an official TrackEval/HOTA replica."""

from collections import Counter
from dataclasses import dataclass
from math import inf
from typing import Any

from .detection import Box, ObjectClass
from .detection_metrics import iou
from .tracking_assignment import assign


@dataclass(frozen=True)
class LabeledBox:
    identity: str
    category: ObjectClass
    box: Box


def evaluate_sequence(
    frames: list[tuple[tuple[LabeledBox, ...], tuple[LabeledBox, ...]]],
) -> dict[str, Any]:
    """Class-aware IoU>=.5; no ignore regions. Global IDs maximize matched observations.

    Transparent identity F1, not official MOTChallenge output. The caller must
    declare whether predicted-only states are included. IDs are clip-local.
    """
    truth_counts: Counter[str] = Counter()
    prediction_counts: Counter[str] = Counter()
    cooccurrence: Counter[tuple[str, str]] = Counter()
    last: dict[str, str] = {}
    interrupted: set[str] = set()
    switches = fragments = tp = fp = fn = duplicates = 0
    overlap_sum = 0.0
    matched_by_truth: Counter[str] = Counter()
    for truth, predictions in frames:
        if len({g.identity for g in truth}) != len(truth) or len(
            {p.identity for p in predictions}
        ) != len(predictions):
            raise ValueError("Duplicate per-frame identity")
        truth_counts.update(g.identity for g in truth)
        prediction_counts.update(p.identity for p in predictions)
        costs = [
            [
                1 - iou(g.box, p.box)
                if g.category == p.category and iou(g.box, p.box) >= 0.5
                else inf
                for p in predictions
            ]
            for g in truth
        ]
        # Prefer maximal valid match count before overlap quality. The dummy
        # penalty exceeds the sum of all possible valid overlap costs.
        matches = assign(costs, float(len(truth) + 1))
        matched_gt, matched_pred = {i for i, _ in matches}, {j for _, j in matches}
        tp += len(matches)
        fp += len(predictions) - len(matches)
        fn += len(truth) - len(matches)
        for i, j in matches:
            g, p = truth[i], predictions[j]
            overlap_sum += 1 - costs[i][j]
            cooccurrence[g.identity, p.identity] += 1
            matched_by_truth[g.identity] += 1
            if g.identity in last and last[g.identity] != p.identity:
                switches += 1
            if g.identity in interrupted:
                fragments += 1
                interrupted.remove(g.identity)
            last[g.identity] = p.identity
        interrupted.update(
            g.identity for i, g in enumerate(truth) if i not in matched_gt and g.identity in last
        )
        duplicates += sum(
            any(g.category == p.category and iou(g.box, p.box) >= 0.5 for g in truth)
            for j, p in enumerate(predictions)
            if j not in matched_pred
        )
    gt_ids, pred_ids = sorted(truth_counts), sorted(prediction_counts)
    maximum = max(cooccurrence.values(), default=0)
    identity_matches = assign(
        [[maximum - cooccurrence[g, p] for p in pred_ids] for g in gt_ids], maximum + 0.5
    )
    idtp = sum(cooccurrence[gt_ids[i], pred_ids[j]] for i, j in identity_matches)
    total_gt, total_pred = sum(truth_counts.values()), sum(prediction_counts.values())
    return {
        "matching_policy": "CLASS_AWARE_IOU_0.5_GLOBAL_ID_COUNTS",
        "frames": len(frames),
        "ground_truth_observations": total_gt,
        "predicted_observations": total_pred,
        "ground_truth_tracks": len(gt_ids),
        "predicted_tracks": len(pred_ids),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "id_switches": switches,
        "fragmentations": fragments,
        "duplicate_observations": duplicates,
        "identity_tp": idtp,
        "identity_fp": total_pred - idtp,
        "identity_fn": total_gt - idtp,
        "identity_precision": idtp / total_pred if total_pred else None,
        "identity_recall": idtp / total_gt if total_gt else None,
        "identity_f1": 2 * idtp / (total_gt + total_pred) if total_gt + total_pred else None,
        "track_recall": sum(matched_by_truth[g] > 0 for g in gt_ids) / len(gt_ids)
        if gt_ids
        else None,
        "mostly_tracked": sum(matched_by_truth[g] / truth_counts[g] >= 0.8 for g in gt_ids),
        "mostly_lost": sum(matched_by_truth[g] / truth_counts[g] <= 0.2 for g in gt_ids),
        "false_track_ids": sum(not any(cooccurrence[g, p] for g in gt_ids) for p in pred_ids),
        "mota_like": 1 - (fp + fn + switches) / total_gt if total_gt else None,
        "mean_matched_iou": overlap_sum / tp if tp else None,
    }
