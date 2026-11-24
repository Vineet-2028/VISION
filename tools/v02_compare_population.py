"""Complete fixed-population comparison and pseudo-label review queue."""

import argparse
import json
from pathlib import Path

from v02_candidate_population import digest, source_targets
from v02_score_population import score


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", nargs="+", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--population", type=Path, default=Path("benchmark-results/v02/populations-02.json")
    )
    args = parser.parse_args()
    population = json.loads(args.population.read_text())
    reports, summaries = {}, {}
    for run in args.runs:
        summary = json.loads((run / "summary.json").read_text())
        if summary["population_sha256"] != digest(args.population) or summary[
            "predictions_sha256"
        ] != digest(run / "predictions.jsonl"):
            raise ValueError("Comparison artifact hash mismatch")
        model = summary["model"]
        if model in reports:
            raise ValueError("Duplicate model identity")
        predictions = {}
        with (run / "predictions.jsonl").open() as stream:
            for line in stream:
                row = json.loads(line)
                if row["source_ns"] in predictions:
                    raise ValueError("Duplicate source frame")
                predictions[row["source_ns"]] = row["regions"]
        reports[model] = score(population, predictions)
        summaries[model] = summary
    teacher = "IDEA-Research/grounding-dino-base"
    required = {
        teacher,
        "rescued-picodet-s",
        "yoloe-26n-prompt-free",
        "yoloe-11s-prompt-free",
        "yolov8s-worldv2",
    }
    if set(reports) != required:
        raise ValueError("Comparison requires PicoDet, three candidates and teacher")
    rows = []
    for index, original in enumerate(population["alerts"]):
        evidence = {name: report["alerts"]["rows"][index] for name, report in reports.items()}
        concepts = {name: row["specific_concept"] for name, row in evidence.items()}
        normalized = {
            name: value.strip().casefold() if value else None for name, value in concepts.items()
        }
        disagreement = len(set(normalized.values())) > 1
        rows.append(
            {
                "alert_id": original["alert_id"],
                "source_observation_ns": original["source_observation_ns"],
                "track_id": original["track_id"],
                "status": "MODEL_PSEUDO_LABEL_REVIEW_REQUIRED",
                "model_evidence": evidence,
                "semantic_disagreement": disagreement,
                "teacher_exact_label_agreement": {
                    name: normalized[name] is not None and normalized[name] == normalized[teacher]
                    for name in normalized
                    if name != teacher
                },
            }
        )
    output = {
        "status": "FIXED_POPULATION_PROXY_COMPARISON_NOT_RELEASE_QUALIFICATION",
        "population_sha256": digest(args.population),
        "alert_denominator": 60,
        "event_denominator": 188,
        "models": reports,
        "runtime_summaries": summaries,
        "alerts": rows,
        "review_queue": [
            r["alert_id"]
            for r in rows
            if r["semantic_disagreement"]
            or any(e["specific_concept"] is None for e in r["model_evidence"].values())
        ],
        "actual_new_runtime_generic_alert_count": None,
        "baseline_actual_generic_alert_count": 60,
        "semantic_accuracy_measured": False,
        "model_adopted": False,
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "comparison.json").write_text(json.dumps(output, indent=2))
    lines = [
        "# Fixed-population model comparison",
        "",
        "Overlap/name-availability proxies, not semantic accuracy or authorized speech.",
        "",
        "| Model | Named /60 | Generic or unmatched /60 | Events /188 | P95 ms | Runtime |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for name, report in reports.items():
        summary = summaries[name]
        runtime = summary.get("provider", str(summary.get("runtime", {}).get("providers")))
        lines.append(
            f"| {name} | {report['alerts']['specific_concept_count']} | "
            f"{report['alerts']['generic_count']} | {report['events']['entity_covered']} | "
            f"{summary['call_time']['p95_ns'] / 1e6:.1f} | {runtime} |"
        )
    lines += [
        "",
        f"All 60 alerts and 188 events were retained. All {len(source_targets(population))} "
        "source frames were evaluated; "
        "missing outputs fail scoring.",
        "",
        "PicoDet spoke 60 generic alerts despite available detector names. The table measures "
        "name availability, not warning specificity. A new realtime profile is not measured here.",
        "",
        "Event coverage means at least one reference-frame IoU >= 0.5, independent of class. "
        "It differs from the realtime linked-stage funnel, tracking continuity and hazard recall.",
        "",
        "Teacher prompts were mined from these same candidate frames. Labels are adaptive "
        "pseudo-labels, not held-out truth. Exact disagreement preserves synonyms and mistakes.",
        "",
        "CPU screening and GPU teacher timings use different runtimes, not an architecture "
        "ranking. Teacher times include cold calls and concurrent checks; resumed VRAM peak "
        "covers only the final process segment.",
        "",
        f"Review queue: {len(output['review_queue'])}/60 alerts. "
        "No review was automatically marked human-validated.",
    ]
    (args.output / "comparison.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"alerts": 60, "events": 188, "review_queue": len(output["review_queue"])}))


if __name__ == "__main__":
    main()
