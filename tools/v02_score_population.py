"""Class-independent overlap proxies on all frozen events; never semantic accuracy."""

import argparse
import json
from collections import Counter
from pathlib import Path

from v02_candidate_population import digest, source_targets


def overlap(a, b):
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(
        0, min(a[3], b[3]) - max(a[1], b[1])
    )
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - intersection
    return intersection / union if union > 0 else 0.0


def match(regions, box):
    candidates = [(overlap(r["box"], box), i, r) for i, r in enumerate(regions)]
    matches = [c for c in candidates if c[0] >= 0.5]
    selected = max(matches, key=lambda c: (c[0], c[2]["confidence"], -c[1]), default=None)
    concept = selected[2]["concept"] if selected else None
    known = bool(concept and concept.strip().casefold() not in {"unknown", "object"})
    return {
        "entity_match": selected is not None,
        "specific_concept": concept if known else None,
        "candidate_index": selected[1] if selected else None,
        "confidence": selected[2]["confidence"] if selected else None,
        "confidence_basis": selected[2].get("confidence_basis", "UNAVAILABLE")
        if selected
        else "UNAVAILABLE",
        "best_iou": selected[0] if selected else max((c[0] for c in candidates), default=0),
        "matching_regions": len(matches),
        "extra_overlapping_regions": max(0, len(matches) - 1),
    }


def score(population, predictions):
    if set(predictions) != set(source_targets(population)):
        raise ValueError("Candidate must cover exactly every source frame, including empty outputs")
    alerts = []
    for alert in population["alerts"]:
        if (
            alert["entity_observed_ns"] != alert["source_observation_ns"]
            or alert["entity_observation_status"] != "OBSERVED"
        ):
            raise ValueError("Alert box is not original observed evidence")
        box = [alert["entity_box"][k] for k in ("x1", "y1", "x2", "y2")]
        alerts.append(
            {
                "alert_id": alert["alert_id"],
                **match(predictions[alert["source_observation_ns"]], box),
            }
        )
    events = []
    for event in population["events"]:
        outcomes = [
            match(predictions[o["observation_ns"]], o["reference_box"])
            for o in event["observations"]
        ]
        names = Counter(
            o["specific_concept"] for o in outcomes if o["specific_concept"] is not None
        )
        events.append(
            {
                "event_id": event["event_id"],
                "observations": len(outcomes),
                "matched_observations": sum(o["entity_match"] for o in outcomes),
                "specific_observations": sum(o["specific_concept"] is not None for o in outcomes),
                "concept_counts": dict(names),
                "dominant_concept_share_among_named_matches": max(names.values())
                / sum(names.values())
                if names
                else None,
                "extra_overlapping_regions": sum(o["extra_overlapping_regions"] for o in outcomes),
            }
        )
    specific = sum(a["specific_concept"] is not None for a in alerts)
    return {
        "status": "OVERLAP_AND_NAME_AVAILABILITY_PROXY_NOT_ACCURACY",
        "alerts": {
            "denominator": 60,
            "specific_concept_count": specific,
            "group_only_count": 0,
            "generic_count": 60 - specific,
            "unknown_or_no_matching_entity_count": 60 - specific,
            "no_matching_entity_count": sum(not a["entity_match"] for a in alerts),
            "rows": alerts,
        },
        "events": {
            "denominator": 188,
            "entity_covered": sum(e["matched_observations"] > 0 for e in events),
            "specific_covered": sum(e["specific_observations"] > 0 for e in events),
            "rows": events,
        },
        "limitations": [
            "Names are predictions, not reviewed labels or authorized alert phrases",
            "Group resolver not qualified; group-only count is not an accuracy measurement",
            "Any-reference-frame event coverage is not continuous trackability",
            "Overlap can match a wrong object/class; teacher consensus is not ground truth",
            "Extra overlaps are duplicate candidates, not proven duplicate objects",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--population", type=Path, default=Path("benchmark-results/v02/populations-02.json")
    )
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    population = json.loads(args.population.read_text())
    summary = json.loads((args.run / "summary.json").read_text())
    if summary["population_sha256"] != digest(args.population) or summary[
        "predictions_sha256"
    ] != digest(args.run / "predictions.jsonl"):
        raise ValueError("Candidate provenance mismatch")
    predictions = {}
    with (args.run / "predictions.jsonl").open() as stream:
        for line in stream:
            row = json.loads(line)
            if row["source_ns"] in predictions:
                raise ValueError("Duplicate source frame")
            predictions[row["source_ns"]] = row["regions"]
    result = score(population, predictions)
    result["model"] = summary["model"]
    with (args.output or (args.run / "population-score.json")).open("x") as stream:
        json.dump(result, stream, indent=2)
    print(
        json.dumps(
            {
                "model": result["model"],
                "specific_proxy": result["alerts"]["specific_concept_count"],
                "generic_proxy": result["alerts"]["generic_count"],
                "entity_events": result["events"]["entity_covered"],
            }
        )
    )


if __name__ == "__main__":
    main()
