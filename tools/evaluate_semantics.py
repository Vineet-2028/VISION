"""Validate a hash-bound human review and score frozen model proposals per split."""

import argparse
import hashlib
import json
from pathlib import Path

from perception_lab.config import read_json
from perception_lab.semantic_evaluation import decode_runs, evaluate_masks
from perception_lab.semantics import TAXONOMY


def evaluate(draft_path, review_path, output):
    if output.exists():
        raise ValueError("Preserve previous evaluation; choose new output")
    draft = read_json(draft_path, max_bytes=100_000_000)
    review = read_json(review_path, max_bytes=100_000_000)
    if (
        draft["schema_version"] != 1
        or review["schema_version"] != 1
        or draft["taxonomy"] != TAXONOMY
        or review["taxonomy"] != TAXONOMY
        or draft["manifest_sha256"] != review["manifest_sha256"]
        or len(draft["frames"]) != len(review["frames"])
    ):
        raise ValueError("Review packet mismatch")
    results = []
    ids = set()
    for original, checked in zip(draft["frames"], review["frames"], strict=True):
        for key in (
            "image_id",
            "sequence_id",
            "split",
            "observation_ns",
            "sha256",
            "width",
            "height",
        ):
            if original[key] != checked[key]:
                raise ValueError("Review frame identity changed")
        if original["image_id"] in ids:
            raise ValueError("Duplicate image identity")
        ids.add(original["image_id"])
        path = (draft_path.parent / original["image"]).resolve()
        if (
            not path.is_relative_to(draft_path.parent.resolve())
            or hashlib.sha256(path.read_bytes()).hexdigest() != original["sha256"]
        ):
            raise ValueError("Frame content mismatch")
        if checked["review_status"] != "HUMAN_REVIEWED":
            raise ValueError("HUMAN_SEGMENTATION_GROUND_TRUTH_REVIEW_REQUIRED")
        width, height = original["width"], original["height"]
        truth = decode_runs(checked["review_runs"], width, height)
        for name, runs in original["predictions"].items():
            predicted = decode_runs(runs, width, height)
            results.append(
                {
                    "image_id": original["image_id"],
                    "split": original["split"],
                    "provider": name,
                    "metrics": evaluate_masks(
                        predicted, truth, review_status=checked["review_status"]
                    ),
                }
            )
    report = {
        "schema_version": 1,
        "taxonomy": TAXONOMY,
        "draft_sha256": hashlib.sha256(draft_path.read_bytes()).hexdigest(),
        "review_sha256": hashlib.sha256(review_path.read_bytes()).hexdigest(),
        "scope": "PARTIAL_HUMAN_LABELS; review attestation is not independent audit",
        "frames": len(ids),
        "results": results,
        "selection": "PENDING_PER_SPLIT_ANALYSIS; no automatic deployment approval",
    }
    output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("draft", "review", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    evaluate(args.draft, args.review, args.output)
