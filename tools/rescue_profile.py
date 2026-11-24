"""Post-hoc critical-path ages; nested spans are never added as exclusive CPU work."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from v0_analyze import quantiles


def stages(row):
    timing = row.get("timing", {})
    pairs = (
        ("decode", "decode_started_ns", "decode_completed_ns"),
        ("acquisition_and_conversion", "decode_completed_ns", "pipeline_accepted_ns"),
        ("queue_wait", "pipeline_accepted_ns", "preprocess_started_ns"),
        ("preprocess", "preprocess_started_ns", "preprocess_completed_ns"),
        ("scheduler", "preprocess_completed_ns", "component_started_ns"),
    )
    result = [
        (name, timing[start], timing[end])
        for name, start, end in pairs
        if start in timing and end in timing
    ]
    for index, component in enumerate(row.get("components", [])):
        name = component.get("component_type", "synchronous_provider_" + str(index + 1))
        result.append((name, component["started_ns"], component["completed_ns"]))
    for span in row.get("spans", []):
        if span["stage"] in {
            "tracking",
            "world_model",
            "corridor",
            "trajectory",
            "interaction",
            "risk",
            "attention",
            "alerts",
            "ego_motion",
            "surface_extraction",
        }:
            result.append((span["stage"], span["end_ns"] - span["duration_ns"], span["end_ns"]))
    return sorted(result, key=lambda item: item[2])


def first_failure(row, budget_ns=500_000_000):
    due = row["due_monotonic_ns"]
    if due is None:
        return "UNAVAILABLE_OFFLINE"
    failure = next((name for name, _, end in stages(row) if end - due > budget_ns), None)
    if failure is not None:
        return failure
    return "publication" if row.get("publication_monotonic_ns", due) - due > budget_ns else "NONE"


def analyze(directory, output):
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest["status"] != "COMPLETE":
        raise ValueError("Incomplete replay")
    output.mkdir(parents=True, exist_ok=False)
    timings = defaultdict(lambda: defaultdict(list))
    failures = Counter()
    with (
        (directory / "updates.jsonl").open(encoding="utf-8") as source,
        (output / "freshness.jsonl").open("x", encoding="utf-8") as sink,
    ):
        for line in source:
            row = json.loads(line)
            due = row["due_monotonic_ns"]
            for name, start, end in stages(row):
                timings[name]["duration_ns"].append(end - start)
                if due is not None:
                    if start >= due:
                        timings[name]["input_age_ns"].append(start - due)
                    if end >= due:
                        timings[name]["output_age_ns"].append(end - due)
            failure = first_failure(row)
            failures[failure] += 1
            sink.write(
                json.dumps({"frame": row["identity"], "FIRST_FRESHNESS_FAILURE_STAGE": failure})
                + "\n"
            )
    report = {
        "source_sha256": manifest["source_sha256"],
        "mode": manifest["mode"],
        "freshness_probe_ns": 500_000_000,
        "first_freshness_failure": dict(failures),
        "stages": {
            stage: {key: quantiles(values) for key, values in fields.items()}
            for stage, fields in timings.items()
        },
        "async_workers": manifest["session"]["summary"].get("enrichment_compute"),
        "async_delivered_ages": manifest["session"]["summary"].get("enrichment_delivered_timing"),
        "limitations": [
            "Acquisition/conversion span includes pacing and frame ownership work",
            "Async delivered ages exclude replaced completed results",
            "Missing worker waits/ages are unavailable, never invented zeros",
            "Prefetch before source due time has unavailable input age",
            "These are engineering freshness observations, not safety thresholds",
        ],
    }
    (output / "profile.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.run, args.output)
