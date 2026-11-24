"""Analyze streamed V0 observations against explicitly limited prototype references."""

import argparse
import bisect
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

from perception_lab.v0_evaluation import (
    STAGES,
    LabelStatus,
    StageOutcome,
    V0EventLedger,
    first_failure,
    quadrant,
    summarize_events,
)


def quantiles(values):
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "scope": "whole_run_exact",
        "max_ns": max(ordered, default=None),
        "mean_ns": sum(ordered) / len(ordered) if ordered else None,
        **{
            f"p{q}_ns": ordered[math.ceil(q / 100 * len(ordered)) - 1] if ordered else None
            for q in (50, 90, 95, 99)
        },
    }


def iou(box, reference):
    x1, y1, x2, y2 = [box[k] for k in ("x1", "y1", "x2", "y2")]
    a, b, c, d = reference
    intersection = max(0, min(x2, c) - max(x1, a)) * max(0, min(y2, d) - max(y1, b))
    union = max(0, x2 - x1) * max(0, y2 - y1) + max(0, c - a) * max(0, d - b) - intersection
    return intersection / union if union else 0


def references(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    events = {}
    frames = sorted(data["frames"], key=lambda f: f["observation_ns"])
    for frame in frames:
        for annotation in frame["annotations"]:
            key = f"{frame['clip_id']}:{annotation['ground_truth_track_id']}"
            event = events.setdefault(
                key,
                {
                    "id": key,
                    "start": frame["observation_ns"],
                    "end": frame["observation_ns"],
                    "relevant": False,
                    "category": annotation["label"],
                    "best": [False] * len(STAGES),
                    "times": [None] * len(STAGES),
                    "ages": [None] * len(STAGES),
                    "matched_track_ids": set(),
                    "observations": 0,
                    "timely": None,
                },
            )
            event["end"] = frame["observation_ns"]
            x1, _, x2, y2 = annotation["box"]
            event["relevant"] |= (
                0.4 <= (x1 + x2) / (2 * frame["width"]) <= 0.6 and y2 / frame["height"] >= 0.65
            )
    return frames, events


def linked_stages(row, annotation):
    """Same-frame linked object chain; no OR across unrelated entities."""
    label, box = annotation["label"], annotation["box"]
    detector = row.get("detector") or {}
    detected = any(
        d["label"] == label and iou(d["box"], box) >= 0.5 for d in detector.get("detections", [])
    )
    tracks = [
        t
        for t in (row.get("tracks") or {}).get("tracks", [])
        if t["category"] == label
        and t["observation_status"] == "OBSERVED"
        and iou(t["bbox"], box) >= 0.5
    ]
    track = max(tracks, key=lambda t: iou(t["bbox"], box), default=None)
    track_id = track["track_id"] if track else None
    entities = (row.get("world") or {}).get("entities", [])
    entity = next(
        (e for e in entities if track_id is not None and e["source_track_id"] == track_id), None
    )
    entity_id = entity["entity_id"] if entity else None

    def linked(container, key):
        return [
            v
            for v in (row.get(container) or {}).get(key, [])
            if entity_id is not None and v.get("entity_id") == entity_id
        ]

    corridor = any(
        v["relation"] not in {"UNKNOWN", "UNAVAILABLE"}
        for v in linked("corridor_analysis", "entity_relations")
    )
    trajectory = bool(linked("trajectory_set", "trajectories"))
    interaction = any(
        v["interaction_type"] not in {"REMAIN_OUTSIDE", "UNAVAILABLE", "UNKNOWN"}
        for v in linked("interaction_analysis", "entity_interactions")
    )
    risk = any(
        v["risk_level"] not in {"UNDETERMINED", "NONE", "LOW"}
        for v in linked("risk_assessment_set", "assessments")
    )
    attention = any(v["decision"] != "SILENT" for v in linked("attention_decision_set", "selected"))
    outputs = [
        v
        for v in (row.get("alert_output_set") or {}).get("outputs", [])
        if entity_id is not None and (v.get("intent") or {}).get("entity_id") == entity_id
    ]
    intent = any(v.get("intent") is not None for v in outputs)
    valid = any(v.get("presentation") is not None and v["status"] == "READY" for v in outputs)
    delivered = any(v["delivered"] for v in outputs)
    flags = [
        detected,
        track is not None,
        entity is not None,
        corridor,
        trajectory,
        interaction,
        risk,
        attention,
        intent,
        valid,
        delivered,
    ]
    # A complete path is only as long as its first failure, even if an upstream
    # cached entity allows a later stage to run. Secondary flags remain in JSONL.
    prefix = []
    for flag in flags:
        prefix.append(flag and (not prefix or prefix[-1]))
    return prefix, track_id


def analyze(directory, reference_path, review_path=None, output=None, existing_review=None):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "COMPLETE":
        raise ValueError("Refuse to score an incomplete replay")
    reference_metadata = json.loads(reference_path.read_text(encoding="utf-8"))
    if reference_metadata["source_sha256"] != manifest["source_sha256"]:
        raise ValueError("Reference source hash does not match replay")
    if review_path:
        review_metadata = json.loads(review_path.read_text(encoding="utf-8"))
        if review_metadata["source_sha256"] != manifest["source_sha256"]:
            raise ValueError("Review source hash does not match replay")
        if any(w.get("review_label") is not None for w in review_metadata["windows"]):
            raise ValueError("Reviewed packet needs adjudication; draft importer cannot relabel it")
    frames, events = references(reference_path)
    output = directory if output is None else output
    if output != directory:
        output.mkdir(parents=True, exist_ok=False)
    window_packets = []
    for path, kind in ((review_path, "blind"), (existing_review, "historical")):
        if path:
            packet = json.loads(path.read_text(encoding="utf-8"))
            if packet["source_sha256"] != manifest["source_sha256"]:
                raise ValueError("Window source mismatch")
            for w in packet["windows"]:
                if w.get("review_label") is not None:
                    raise ValueError("Reviewed labels require adjudication")
                window_packets.append(
                    {
                        **w,
                        "id": f"{kind}-{w['id']}",
                        "population": kind,
                        "current_updates": 0,
                        "current_alerts": 0,
                    }
                )
    timestamps = [f["observation_ns"] for f in frames]
    durations, ages = defaultdict(list), defaultdict(list)
    first_stale, dispositions, alert_counts, phrases = Counter(), Counter(), Counter(), Counter()
    attention_actions, episode_ids = Counter(), set()
    intervals, critical = [], []
    previous = None
    updates = 0
    samples = {"success": [], "failure": []}
    with (directory / "updates.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            updates += 1
            source = row["identity"]["observation_ns"]
            published = row["publication_monotonic_ns"]
            if previous is not None:
                intervals.append(published - previous)
            previous = published
            due = row["due_monotonic_ns"]
            stage_ages = {}
            for span in row["spans"]:
                name = span["stage"]
                durations[name].append(span["duration_ns"])
                if due is not None and name in {
                    "world_model",
                    "corridor",
                    "trajectory",
                    "interaction",
                    "risk",
                    "attention",
                    "alerts",
                }:
                    age = max(0, span["end_ns"] - due)
                    ages[name].append(age)
                    stage_ages[name] = age
            if due is not None:
                ages["publication"].append(published - due)
                provider_stale = next(
                    (
                        f"PROVIDER_{index + 1}"
                        for index, component in enumerate(row["components"])
                        if component["completed_ns"] - due > 500_000_000
                    ),
                    None,
                )
                stale = next(
                    (
                        s
                        for s in (
                            "world_model",
                            "corridor",
                            "trajectory",
                            "interaction",
                            "risk",
                            "attention",
                            "alerts",
                        )
                        if stage_ages.get(s, 0) > 500_000_000
                    ),
                    None,
                )
                first_stale[provider_stale or stale or "NONE"] += 1
            # Synchronous provider intervals are nonoverlapping. Postprocess includes
            # reasoning: never add it again to nested per-stage times.
            providers = sum(c["completed_ns"] - c["started_ns"] for c in row["components"])
            critical.append(
                {
                    "source_ns": source,
                    "provider_ns": providers,
                    "postprocess_ns": next(
                        (s["duration_ns"] for s in row["spans"] if s["stage"] == "postprocess"), 0
                    ),
                    "source_age_ns": row["source_to_publication_age_ns"],
                }
            )
            for candidate in row["attention_candidates"]:
                dispositions[candidate["disposition"]] += 1
                age = candidate["source_age_at_attention_ns"]
                if age is not None:
                    ages["candidate_at_attention"].append(age)
                    if "EXPIR" in candidate["disposition"]:
                        ages["expired_candidate_at_attention"].append(age)
            outputs = (row.get("alert_output_set") or {}).get("outputs", [])
            for decision in (row.get("attention_decision_set") or {}).get("selected", []):
                attention_actions[decision["decision"]] += 1
                if decision.get("event"):
                    episode_ids.add(decision["event"]["episode_id"])
            for window in window_packets:
                if window["start_seconds"] * 1e9 <= source < window["end_seconds"] * 1e9:
                    window["current_updates"] += 1
                    window["current_alerts"] += sum(o["delivered"] for o in outputs)
            for alert_output in outputs:
                alert_counts[alert_output["status"]] += 1
                alert_counts["text_sink_accepted"] += alert_output["delivered"]
                if alert_output.get("presentation"):
                    phrases[alert_output["presentation"]["speech_text"]] += 1
            kind = "success" if any(v["delivered"] for v in outputs) else "failure"
            if len(samples[kind]) < 10 and (
                not samples[kind] or source - samples[kind][-1]["source_ns"] >= 6_000_000_000
            ):
                samples[kind].append(
                    {
                        "source_ns": source,
                        "sequence": row["identity"]["sequence"],
                        "criterion": "text sink accepted"
                        if kind == "success"
                        else "no accepted text alert; not necessarily a miss",
                        "diagnostics": {
                            "outputs": outputs,
                            "selected_attention": (row.get("attention_decision_set") or {}).get(
                                "selected", []
                            ),
                            "interaction_examples": (row.get("interaction_analysis") or {}).get(
                                "entity_interactions", []
                            )[:3],
                            "risk_examples": (row.get("risk_assessment_set") or {}).get(
                                "assessments", []
                            )[:3],
                            "world_entities": len((row.get("world") or {}).get("entities", [])),
                            "source_age_ns": row["source_to_publication_age_ns"],
                        },
                    }
                )
            index = bisect.bisect_left(timestamps, source)
            choices = [i for i in (index - 1, index) if 0 <= i < len(frames)]
            nearest = min(choices, key=lambda i: abs(timestamps[i] - source)) if choices else None
            if nearest is None or abs(timestamps[nearest] - source) > 100_000_000:
                continue
            frame = frames[nearest]
            for annotation in frame["annotations"]:
                key = f"{frame['clip_id']}:{annotation['ground_truth_track_id']}"
                event = events[key]
                x1, _, x2, y2 = annotation["box"]
                central = (
                    0.4 <= (x1 + x2) / (2 * frame["width"]) <= 0.6 and y2 / frame["height"] >= 0.65
                )
                if event["relevant"] and not central:
                    continue
                event["observations"] += 1
                if due is not None:
                    event["timely"] = bool(event["timely"]) or published - due <= 500_000_000
                flags, track_id = linked_stages(row, annotation)
                if track_id:
                    event["matched_track_ids"].add(track_id["serial"])
                if sum(flags) > sum(event["best"]):
                    event["best"] = flags
                for index, flag in enumerate(flags):
                    if flag and event["times"][index] is None:
                        event["times"][index] = source
                        if due is not None:
                            names = (
                                "component",
                                "tracking",
                                "world_model",
                                "corridor",
                                "trajectory",
                                "interaction",
                                "risk",
                                "attention",
                                "alerts",
                                "alerts",
                                "alerts",
                            )
                            end = next(
                                (s["end_ns"] for s in row["spans"] if s["stage"] == names[index]),
                                None,
                            )
                            event["ages"][index] = max(0, end - due) if end is not None else None
    ledger = []
    for event in events.values():
        stages = tuple(
            StageOutcome(
                name,
                "PASS" if event["best"][i] else "FAIL",
                event["times"][i],
                event["ages"][i],
                "NO_ALIGNED_RUNTIME_OBSERVATION" if i == 0 and not event["observations"] else None,
            )
            for i, name in enumerate(STAGES)
        )
        failure, reason = first_failure(stages)
        ledger.append(
            V0EventLedger(
                event["id"],
                manifest["source_sha256"],
                event["start"],
                event["end"],
                LabelStatus.PROXY,
                event["relevant"],
                event["category"],
                "CENTRAL_LOWER_IMAGE_OCCUPANCY_PROXY",
                None,
                stages,
                failure,
                reason,
                next(
                    (
                        STAGES[i]
                        for i, age in enumerate(event["ages"])
                        if age is not None and age > 500_000_000
                    ),
                    None,
                ),
                "ACCEPTED" if event["best"][-1] else "NOT_ACCEPTED",
                quadrant(event["best"][-1], event["timely"]),
                "Task007 prototype draft-origin identity annotations; "
                "central lower image heuristic; NOT hazard truth",
                (
                    "Matching: class+IoU>=0.5, nearest annotation<=100ms; same-frame linked prefix",
                    f"Matched runtime track IDs: {len(event['matched_track_ids'])}; "
                    "multiple IDs may indicate fragmentation",
                    "Stage ages reference matched current-frame PTS; "
                    "older evidence ages are separate raw diagnostics",
                ),
            )
        )
    if window_packets:
        for window in window_packets:
            stages = tuple(StageOutcome(s, "UNKNOWN") for s in STAGES)
            failure, reason = first_failure(stages)
            ledger.append(
                V0EventLedger(
                    str(window["id"]),
                    manifest["source_sha256"],
                    int(window["start_seconds"] * 1e9),
                    int(window["end_seconds"] * 1e9),
                    LabelStatus.DRAFT,
                    None,
                    "UNKNOWN",
                    "UNKNOWN",
                    None,
                    stages,
                    failure,
                    reason,
                    None,
                    "UNASSESSED",
                    "UNKNOWN",
                    f"{window['population']} timestamp window; review pending",
                )
            )
    with (output / "event-ledger.jsonl").open("x", encoding="utf-8") as stream:
        for event in ledger:
            stream.write(json.dumps(asdict(event)) + "\n")
    with (output / "critical-path.jsonl").open("x", encoding="utf-8") as stream:
        for item in critical:
            stream.write(json.dumps(item) + "\n")
    report = {
        "schema_version": 1,
        "updates": updates,
        "funnel": summarize_events(tuple(ledger)),
        "compute": {k: quantiles(v) for k, v in durations.items()},
        "source_ages": {k: quantiles(v) for k, v in ages.items()},
        "update_intervals": quantiles(intervals),
        "first_500ms_crossing": dict(first_stale),
        "attention_dispositions": dict(dispositions),
        "alerts": dict(alert_counts),
        "phrases": dict(phrases),
        "burden": {
            "selected_actions": dict(attention_actions),
            "selected_episodes": len(episode_ids),
            "text_alerts_per_source_minute": alert_counts["text_sink_accepted"]
            * 60
            / manifest["requested_seconds"],
            "false_alert_rate": None,
            "missed_hazards": None,
            "human_lead_time": None,
        },
        "examples": samples,
        "draft_window_results": window_packets,
        "limitations": [
            "One video; prototype references are not human interaction ground truth",
            "Stage ages use current frame PTS; older evidence age is retained in raw traces",
            "Metric spans may nest; do not sum all timing entries",
            "No audio, hazard recall, physical safety, false-alert truth or usefulness claim",
        ],
    }
    (output / "analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--existing-review", type=Path)
    args = parser.parse_args()
    analyze(args.run, args.references, args.review, args.output, args.existing_review)
