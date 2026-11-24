"""Score complete exact-frame offline probes; association overlap is not identity truth."""

import argparse
import json
from collections import Counter
from pathlib import Path

from v02_candidate_population import digest, source_targets
from v02_score_population import overlap


def assess(row, box):
    entities = (row.get("world") or {}).get("entities", [])
    candidates = [
        (overlap([e["box"][k] for k in ("x1", "y1", "x2", "y2")], box), e) for e in entities
    ]
    matches = [(iou, e) for iou, e in candidates if iou >= 0.5]
    matches.sort(key=lambda item: (-item[0], item[1]["entity_id"]["serial"]))
    if not matches:
        return {
            "entity": False,
            "semantic_state": "UNAVAILABLE",
            "presentation": "NOT_PRESENTED",
            "authorization_reason": "NO_ASSOCIATION",
            "first_loss_stage": "TRACK_ASSOCIATION",
        }
    best, entity = matches[0]
    identity = entity["entity_id"]
    state = entity.get("track_semantics")
    semantic_state = (
        "SPECIFIC"
        if state and state["quality"] == "STABLE" and state["selected_concept"]
        else "GROUP"
        if state and state.get("group_quality") == "STABLE"
        else "UNSTABLE"
        if state and state["quality"] == "UNSTABLE"
        else "UNAVAILABLE"
    )
    attention = row.get("attention_decision_set") or {}
    decisions = attention.get("selected", []) + [
        s["decision"] for s in attention.get("suppressed", [])
    ]
    decision = next((d for d in decisions if d["entity_id"] == identity), None)
    outputs = [
        o
        for o in (row.get("alert_output_set") or {}).get("outputs", [])
        if o.get("delivered") and o.get("intent") and o["intent"]["entity_id"] == identity
    ]
    stage_fields = {
        "corridor": ("corridor_analysis", "entity_relations"),
        "trajectory": ("trajectory_set", "trajectories"),
        "interaction": ("interaction_analysis", "entity_interactions"),
        "risk": ("risk_assessment_set", "assessments"),
    }
    stages = {
        name: any(v["entity_id"] == identity for v in (row.get(container) or {}).get(field, []))
        for name, (container, field) in stage_fields.items()
    }
    return {
        "entity": True,
        "track": True,
        "world": True,
        **stages,
        "attention": decision is not None,
        "alert": bool(outputs),
        "entity_id": identity,
        "source_track_id": entity["source_track_id"],
        "association_basis": "CROSS_RUN_IOU_PROXY_NOT_VERIFIED_IDENTITY",
        "best_iou": best,
        "overlapping_entities": len(matches),
        "semantic_state": semantic_state,
        "track_semantics": state,
        "authorization_reason": decision.get("semantic_authorization_reason", "NOT_RECORDED")
        if decision
        else "NO_ATTENTION_DECISION",
        "presentation": outputs[0]["presentation"].get("semantic_level", "UNRECORDED")
        if outputs
        else "NOT_PRESENTED",
        "speech": [o["presentation"]["speech_text"] for o in outputs],
        "attention_action": decision.get("decision") if decision else None,
        "attention_reasons": decision.get("reason_codes") if decision else None,
        "first_loss_stage": "TRACK_SEMANTIC"
        if semantic_state in {"UNAVAILABLE", "UNSTABLE"}
        else "ATTENTION_SEMANTIC"
        if decision is None or decision.get("semantic_evidence") is None
        else "NONE_SEMANTICS_AUTHORIZED_NO_PRESENTATION"
        if not outputs
        else "NONE",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    population_path = Path("benchmark-results/v02/populations-02.json")
    population = json.loads(population_path.read_text())
    summary = json.loads((args.run / "probe-summary.json").read_text())
    if summary["population_sha256"] != digest(population_path) or summary[
        "updates_sha256"
    ] != digest(args.run / "updates.jsonl"):
        raise ValueError("Probe provenance mismatch")
    targets = set(source_targets(population))
    rows = {}
    delivered = []
    with (args.run / "updates.jsonl").open() as stream:
        for line in stream:
            row = json.loads(line)
            delivered.extend(
                o
                for o in (row.get("alert_output_set") or {}).get("outputs", [])
                if o.get("delivered")
            )
            stamp = row["identity"]["observation_ns"]
            if stamp in targets:
                if stamp in rows:
                    raise ValueError("Duplicate exact frame")
                rows[stamp] = row
    if set(rows) != targets:
        raise ValueError("Missing exact population frame")
    alerts = [
        {
            "alert_id": a["alert_id"],
            "source_ns": a["source_observation_ns"],
            **assess(
                rows[a["source_observation_ns"]],
                [a["entity_box"][k] for k in ("x1", "y1", "x2", "y2")],
            ),
        }
        for a in population["alerts"]
    ]
    events = []
    for event in population["events"]:
        observations = [
            assess(rows[o["observation_ns"]], o["reference_box"]) for o in event["observations"]
        ]
        events.append(
            {
                "event_id": event["event_id"],
                "observations": len(observations),
                "coverage": {
                    key: any(o.get(key, False) for o in observations)
                    for key in (
                        "entity",
                        "track",
                        "world",
                        "corridor",
                        "trajectory",
                        "interaction",
                        "risk",
                        "attention",
                        "alert",
                    )
                },
                "semantic_states": dict(Counter(o["semantic_state"] for o in observations)),
            }
        )
    result = {
        "scope": "REAL_OFFLINE_CONTEXT_PIPELINE_WITH_OVERLAP_ASSOCIATION_NOT_FINAL_QUALIFICATION",
        "population_sha256": digest(population_path),
        "alerts_denominator": 60,
        "events_denominator": 188,
        "before_actual_presentations": {"SPECIFIC": 0, "GROUP": 0, "GENERIC": 60},
        "all_probe_delivered_outputs_different_schedule": dict(
            Counter(o["presentation"].get("semantic_level", "UNRECORDED") for o in delivered)
        ),
        "after_matched_semantic_states": dict(Counter(a["semantic_state"] for a in alerts)),
        "after_matched_actual_presentations": dict(Counter(a["presentation"] for a in alerts)),
        "authorization_reasons": dict(Counter(a["authorization_reason"] for a in alerts)),
        "first_loss_distribution": dict(Counter(a["first_loss_stage"] for a in alerts)),
        "event_coverage": {
            key: sum(e["coverage"][key] for e in events) for key in events[0]["coverage"]
        },
        "alerts": alerts,
        "events": events,
        "limitations": [
            "Unchanged original population; new-run identities linked by declared IoU proxy",
            "No original historical association was reconstructed",
            "NOT_PRESENTED is not counted as generic speech or semantic recovery",
            "Offline context schedule differs from rescued realtime; no accuracy claim",
        ],
    }
    with (args.output or (args.run / "semantic-score.json")).open("x") as out:
        json.dump(result, out, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k not in {"alerts", "events"}}))


if __name__ == "__main__":
    main()
