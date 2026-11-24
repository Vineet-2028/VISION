"""Tracking continuity diagnostics on the same 300 prototype reference frames."""

import argparse
import bisect
import json
from collections import defaultdict
from pathlib import Path

from v0_analyze import quantiles

from perception_lab.detection import Box, ObjectClass
from perception_lab.tracking_evaluation import LabeledBox, evaluate_sequence


def analyze(directory, references, output):
    manifest = json.loads((directory / "manifest.json").read_text())
    reference = json.loads(references.read_text())
    if manifest["status"] != "COMPLETE" or reference["source_sha256"] != manifest["source_sha256"]:
        raise ValueError("Require a complete replay and identical source reference")
    frames = sorted(reference["frames"], key=lambda frame: frame["observation_ns"])
    timestamps = [frame["observation_ns"] for frame in frames]
    selected, lifetimes = {}, {}
    predicted_ages = []
    with (directory / "updates.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            now = row["identity"]["observation_ns"]
            tracks = (row.get("tracks") or {}).get("tracks", [])
            for track in tracks:
                key = track["track_id"]["serial"]
                lifetime = lifetimes.setdefault(key, [now, now])
                lifetime[1] = now
                if track["observation_status"] != "OBSERVED":
                    predicted_ages.append(track["observation_age_ns"])
            index = bisect.bisect_left(timestamps, now)
            for candidate in (index - 1, index):
                if not 0 <= candidate < len(frames):
                    continue
                distance = abs(timestamps[candidate] - now)
                if distance <= 100_000_000 and distance < selected.get(candidate, (10**20, []))[0]:
                    selected[candidate] = (distance, tracks)
    pairs = defaultdict(list)
    for index, frame in enumerate(frames):
        clip = str(frame["clip_id"]) + ":"
        truth = tuple(
            LabeledBox(
                clip + str(a["ground_truth_track_id"]), ObjectClass(a["label"]), Box(*a["box"])
            )
            for a in frame["annotations"]
        )
        predicted = tuple(
            LabeledBox(
                clip + str(t["track_id"]["serial"]), ObjectClass(t["category"]), Box(**t["bbox"])
            )
            for t in selected.get(index, (None, []))[1]
            if t["observation_status"] == "OBSERVED"
        )
        pairs[clip].append((truth, predicted))
    clip_metrics = {clip: evaluate_sequence(rows) for clip, rows in pairs.items()}
    totals = {
        key: sum(row[key] for row in clip_metrics.values())
        for key in (
            "frames",
            "ground_truth_observations",
            "predicted_observations",
            "tp",
            "fp",
            "fn",
            "id_switches",
            "fragmentations",
            "identity_tp",
            "identity_fp",
            "identity_fn",
        )
    }
    denominator = 2 * totals["identity_tp"] + totals["identity_fp"] + totals["identity_fn"]
    totals["identity_f1"] = 2 * totals["identity_tp"] / denominator if denominator else None
    result = {
        "scope": "Prototype identity references, not human-validated tracking ground truth",
        "sampling": "300 fixed reference frames; nearest replay update within 100ms; observed only",
        "references_with_nearby_update": len(selected),
        "identity_metrics": totals,
        "per_clip": clip_metrics,
        "observed_track_lifetimes": quantiles([last - first for first, last in lifetimes.values()]),
        "prediction_only_observation_age": quantiles(predicted_ages),
        "gap_resets": manifest["session"]["summary"]["tracking_peaks"]["gap_resets"],
    }
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.run, args.references, args.output)
