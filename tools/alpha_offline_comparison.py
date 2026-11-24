"""Compare canonical traces on matching source frames without equating session-local IDs."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def compare(baseline, candidate):
    left, right = [
        json.loads((path / "qualification.json").read_text()) for path in (baseline, candidate)
    ]
    if (
        left["identity_sha256"] != right["identity_sha256"]
        or left["source_sha256"] != right["source_sha256"]
    ):
        raise ValueError("Different source population")
    by_view = defaultdict(Counter)
    stage_items = (
        ("detector", "detections"),
        ("tracks", "tracks"),
        ("world", "entities"),
        ("corridor_analysis", "entity_relations"),
        ("trajectory_set", "trajectories"),
        ("interaction_analysis", "entity_interactions"),
        ("risk_assessment_set", "assessments"),
    )
    with (
        (baseline / "replay/updates.jsonl").open(encoding="utf-8") as old,
        (candidate / "replay/updates.jsonl").open(encoding="utf-8") as new,
    ):
        for a, b in zip(old, new, strict=True):
            a, b = json.loads(a), json.loads(b)
            if a["identity"] != b["identity"]:
                raise ValueError("Frame identities differ")
            view = by_view[b["camera_view_quality"]["status"]]
            view["frames"] += 1
            for stage, items in stage_items:
                before = len((a[stage] or {}).get(items, []))
                after = len((b[stage] or {}).get(items, []))
                view[stage + "_baseline"] += before
                view[stage + "_candidate"] += after
                view[stage + "_different_frames"] += before != after
    if sum(group["frames"] for group in by_view.values()) != 18000:
        raise ValueError("Incomplete comparison")
    return {
        "source_sha256": left["source_sha256"],
        "identity_sha256": left["identity_sha256"],
        "stage_counts_by_candidate_view": dict(by_view),
        "scope": "Observation counts on equal frames; no human recall or event matching inferred.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "candidate", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    result = compare(args.baseline, args.candidate)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2)
