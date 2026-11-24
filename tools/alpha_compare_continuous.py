"""Fail-closed paired replay comparison; never associate historical events by boxes."""

import argparse
import json
from collections import Counter
from itertools import zip_longest
from pathlib import Path

from v0_replay import digest


def normalize(value, session):
    if isinstance(value, dict):
        return {
            k: normalize(v, session)
            for k, v in value.items()
            if k
            not in {
                "inference_ns",
                "postprocess_ns",
                "semantic_evidence",
                "semantic_authorization_reason",
            }
        }
    if isinstance(value, list):
        return [normalize(v, session) for v in value]
    if isinstance(value, str):
        return value.replace(session, "PAIRED_SESSION") if session else value
    return value


def count_outputs(row, counts):
    for output in (row.get("alert_output_set") or {}).get("outputs", []):
        if output.get("delivered"):
            presentation = output.get("presentation") or {}
            counts[presentation.get("semantic_level", "UNKNOWN")] += 1


def historical_population_status(population):
    """Keep every frozen marker visible without substituting spatial overlap for identity."""
    result = {}
    for name, key, expected in (("alerts", "alert_id", 60), ("events", "event_id", 188)):
        records = population[name]
        if len(records) != expected or len({r[key] for r in records}) != expected:
            raise ValueError("Historical population denominator/identity mismatch")
        if any(r.get("lineage") is not None for r in records):
            raise ValueError("Historical lineage requires explicit correspondence analysis")
        result[name] = {
            "denominator": expected,
            "corresponded": 0,
            "unresolved": expected,
            "markers": [
                {
                    key: record[key],
                    "status": "UNRESOLVED",
                    "reason": "NO_SHARED_IMMUTABLE_CAUSAL_IDENTITY_RECORDED",
                    "current_semantic_state": None,
                    "current_presentation": None,
                }
                for record in records
            ],
        }
    return result


def compare(a, b):
    summaries = [json.loads((p / "continuous-summary.json").read_text()) for p in (a, b)]
    if [s["arm"] for s in summaries] != ["A", "B"]:
        raise ValueError("Expected A then B")
    for summary in summaries:
        run = summary.get("summary", {})
        counts = run.get("summary", {}).get("frame_counts", {})
        if (
            summary.get("status") != "COMPLETE_CONTINUOUS_OFFLINE_PRESENTATION_ABLATION"
            or not isinstance(summary.get("admitted"), int)
            or summary["admitted"] <= 0
            or run.get("failure") is not None
            or counts.get("failed") != 0
            or counts.get("dropped") != 0
            or counts.get("processed") != summary["admitted"]
            or summary.get("writer_drops") != 0
        ):
            raise ValueError("Complete failure-free replay required for both arms")
    for key in (
        "source_sha256",
        "admission_sha256",
        "seconds",
        "admitted",
        "ontology_sha256",
        "runtime",
    ):
        if summaries[0][key] != summaries[1][key]:
            raise ValueError(f"Paired prerequisite mismatch: {key}")
    configs = [json.loads((p / "configuration.json").read_text()) for p in (a, b)]
    if [c.pop("semantic_presentation_enabled") for c in configs] != [False, True]:
        raise ValueError("Presentation ablation mismatch")
    for config in configs:
        config.pop("output")
    if configs[0] != configs[1]:
        raise ValueError("Configurations differ outside declared presentation ablation")
    if (a / "source-manifest.json").read_text() != (b / "source-manifest.json").read_text():
        raise ValueError("Runtime sources differ between arms")
    for path, summary in zip((a, b), summaries, strict=True):
        if digest(path / "updates.jsonl") != summary["updates_sha256"]:
            raise ValueError("Trace hash mismatch")
    differences, presentations_a, presentations_b, states = (
        Counter(),
        Counter(),
        Counter(),
        Counter(),
    )
    stages = (
        "detector",
        "tracks",
        "world",
        "corridor_analysis",
        "trajectory_set",
        "interaction_analysis",
        "risk_assessment_set",
        "attention_decision_set",
    )
    rows = 0
    with (a / "updates.jsonl").open() as fa, (b / "updates.jsonl").open() as fb:
        for la, lb in zip_longest(fa, fb):
            if la is None or lb is None:
                raise ValueError("Update count mismatch")
            ra, rb = json.loads(la), json.loads(lb)
            for row in (ra, rb):
                if row.get("schema_version") != 2 or row.get("trace_mode", "FULL") != "FULL":
                    raise ValueError("Full schema-2 traces required for stage equivalence")
                if any(stage not in row for stage in stages):
                    raise ValueError("Required physical stage missing from trace")
            if ra["identity"] != rb["identity"]:
                raise ValueError("Authoritative source identity mismatch")
            sa = (ra.get("tracks") or {}).get("session_id", "")
            sb = (rb.get("tracks") or {}).get("session_id", "")
            for stage in stages:
                if normalize(ra.get(stage), sa) != normalize(rb.get(stage), sb):
                    differences[stage] += 1
            count_outputs(ra, presentations_a)
            count_outputs(rb, presentations_b)
            for entity in (rb.get("world") or {}).get("entities", []):
                semantics = entity.get("track_semantics") or {}
                states["WORLD_ENTITY_OBSERVATIONS"] += 1
                states["SPECIFIC_" + semantics.get("quality", "UNAVAILABLE")] += 1
                states["GROUP_" + semantics.get("group_quality", "UNAVAILABLE")] += 1
            rows += 1
    if rows != summaries[0]["admitted"]:
        raise ValueError("Not every admitted frame has a trace update")
    return {
        "status": "PAIRED_PRESENTATION_ABLATION_VERIFIED" if not differences else "PAIR_DIVERGED",
        "updates_per_arm": rows,
        "nonpresentation_differences": dict(differences),
        "A_presentations": dict(presentations_a),
        "B_presentations": dict(presentations_b),
        "B_observation_counts_not_event_counts": dict(states),
        "historical_60_correspondence": "NOT_ESTABLISHED_NO_HEURISTIC_SUBSTITUTION",
        "canonical_188_correspondence": "NOT_ESTABLISHED_NO_HEURISTIC_SUBSTITUTION",
        "limitations": [
            "Presentation-only ablation, both arms retain generic semantic adapter/fusion",
            "Same fixed source-time admission, not realtime qualification",
            "Cross-run session UUIDs normalized, other identity/decision fields compared",
            "Per-update inference timings excluded from deterministic equivalence",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a", type=Path, required=True)
    parser.add_argument("--b", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = compare(args.a, args.b)
    population_path = (
        Path(__file__).resolve().parents[1] / "benchmark-results/v02/populations-02.json"
    )
    population_hash = digest(population_path)
    if population_hash != "49d6b0ab0142d71b7db6b12b64ebcca723e580afad171e7484b2ea69d1c85631":
        raise ValueError("Frozen historical population changed")
    population = json.loads(population_path.read_text())
    summary = json.loads((args.b / "continuous-summary.json").read_text())
    if population["source_sha256"] != summary["source_sha256"]:
        raise ValueError("Historical/current source mismatch")
    report["historical_population_sha256"] = population_hash
    report["historical_marker_correspondence"] = historical_population_status(population)
    report["analyzer_sha256"] = digest(Path(__file__))
    with args.output.open("x") as output:
        json.dump(report, output, indent=2)
    print(json.dumps(report, indent=2))
    if report["status"] == "PAIR_DIVERGED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
