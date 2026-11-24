"""Hash-bound forensic semantic ledger. Missing telemetry is never invented evidence."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def stage(name, record, *, concept=None, basis=None, age=None, reason=None):
    return {
        "stage": name,
        "record_present": record is not None,
        "raw_concept": concept,
        "confidence_basis": basis or "UNKNOWN_NOT_RECORDED",
        "age_ns": age,
        "stability": "UNKNOWN_NOT_RECORDED",
        "source_provider": None,
        "semantic_group": None,
        "authorization_status": "UNKNOWN_NOT_RECORDED",
        "rejection_reason": reason or "UNKNOWN",
        "recorded_evidence": record,
    }


def unique(rows, key, identity):
    matches = [row for row in rows if row.get(key) == identity]
    if len(matches) > 1:
        raise ValueError("Ambiguous entity association")
    return matches[0] if matches else None


def event_ledger(row, output, frozen):
    intent = output["intent"]
    if (
        intent["alert_id"] != frozen["alert_id"]
        or intent["entity_id"] != frozen["entity_id"]
        or intent["source_observation_ns"] != frozen["source_observation_ns"]
        or row["identity"] != frozen["publication_frame"]
    ):
        raise ValueError("Frozen alert association changed")
    entity = unique((row.get("world") or {}).get("entities", []), "entity_id", intent["entity_id"])
    track = unique((row.get("tracks") or {}).get("tracks", []), "track_id", frozen["track_id"])
    detector = row.get("detector") or {}
    # Exact original observation box, not an IoU/name-availability proxy.
    candidates = []
    if track and track.get("observation_status") == "OBSERVED":
        box = track.get("latest_observed_bbox")
        if box and detector.get("identity") == row["identity"]:
            candidates = [
                d
                for d in detector.get("detections", [])
                if all(abs(d["box"][k] - box[k]) <= 1e-6 for k in ("x1", "y1", "x2", "y2"))
            ]
    detection = candidates[0] if len(candidates) == 1 else None
    attention = unique(
        (row.get("attention_decision_set") or {}).get("selected", []),
        "entity_id",
        intent["entity_id"],
    )
    stages = [
        stage(
            "DETECTOR_SEMANTIC",
            detection,
            concept=detection.get("class_name") if detection else None,
            basis="JOINT_DETECTION_SCORE" if detection else None,
            age=0 if detection else None,
            reason="PRESENT_NOT_AUTHORIZED" if detection else "UNKNOWN_DETECTOR_ASSOCIATION",
        ),
        stage(
            "TRACK_SEMANTIC",
            track,
            concept=track.get("category") if track else None,
            basis="TRACK_CATEGORY_VOTE_NOT_CALIBRATED_SEMANTIC_CONFIDENCE" if track else None,
            age=track.get("observation_age_ns") if track else None,
        ),
        stage(
            "WORLD_SEMANTIC",
            entity,
            concept=entity.get("category") if entity else None,
            age=entity.get("observation_age_ns") if entity else None,
        ),
    ]
    for name, container, field in [
        ("INTERACTION_SEMANTIC", "interaction_analysis", "entity_interactions"),
        ("RISK_SEMANTIC", "risk_assessment_set", "assessments"),
    ]:
        record = unique((row.get(container) or {}).get(field, []), "entity_id", intent["entity_id"])
        stages.append(stage(name, record, reason="CLASS_AGNOSTIC_STAGE_NOT_SEMANTIC_AUTHORIZER"))
    stages.append(
        stage(
            "ATTENTION_SEMANTIC",
            attention,
            reason=(
                "SEMANTIC_EVIDENCE_OMITTED_FROM_TRACE"
                if attention is not None and "semantic_evidence" not in attention
                else "SEMANTICS_UNAVAILABLE"
                if attention is not None and attention["semantic_evidence"] is None
                else "UNKNOWN"
            ),
        )
    )
    intent_stage = stage(
        "ALERT_INTENT_SEMANTIC",
        intent,
        concept=intent.get("concept_text"),
        reason="SEMANTICS_UNAVAILABLE"
        if "SEMANTICS_UNAVAILABLE" in intent["reason_codes"]
        else "UNKNOWN",
    )
    if intent_stage["rejection_reason"] == "SEMANTICS_UNAVAILABLE":
        intent_stage["authorization_status"] = "UNAVAILABLE"
    stages.append(intent_stage)
    stages.append(
        stage(
            "ALERT_PRESENTATION_SEMANTIC",
            output.get("presentation"),
            reason="ALERT_POLICY_GENERIC_FALLBACK"
            if output["presentation"]["speech_text"] == "Object."
            else "UNKNOWN",
        )
    )
    return {
        "alert_id": intent["alert_id"],
        "event_id": intent["event_id"],
        "source_observation_ns": intent["source_observation_ns"],
        "entity_id": intent["entity_id"],
        "track_id": frozen["track_id"],
        "stages": stages,
        "first_semantic_loss_stage": "UNKNOWN",
        "first_semantic_loss_reason": "BASELINE_TRACE_OMITTED_AUTHORIZATION_EVIDENCE",
        "first_confirmed_unavailable_stage": "ALERT_INTENT_SEMANTIC"
        if intent_stage["authorization_status"] == "UNAVAILABLE"
        else None,
        "presentation": output["presentation"]["speech_text"],
        "interpretation": (
            "Category presence or track hits do not establish stable authorized semantics"
        ),
    }


def build(population, trace):
    alerts = population["alerts"]
    expected = {a["alert_id"]: a for a in alerts}
    if len(alerts) != 60 or len(expected) != 60:
        raise ValueError("Exact 60-alert denominator required")
    if digest(trace) != population["updates_sha256"]:
        raise ValueError("Frozen trace hash mismatch")
    found = {}
    with trace.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            for output in (row.get("alert_output_set") or {}).get("outputs", []):
                if not output["delivered"]:
                    continue
                aid = output["intent"]["alert_id"]
                if aid not in expected or aid in found:
                    raise ValueError("Unexpected or duplicated delivered alert")
                found[aid] = event_ledger(row, output, expected[aid])
    if set(found) != set(expected):
        raise ValueError("Incomplete alert population")
    events = [found[a["alert_id"]] for a in alerts]
    return {
        "schema": "SemanticEventLedger.v1",
        "scope": "FROZEN_BASELINE_FORENSIC_NOT_RERUN",
        "updates_sha256": population["updates_sha256"],
        "alert_denominator": 60,
        "events": events,
        "first_loss_distribution": dict(Counter(e["first_semantic_loss_stage"] for e in events)),
        "confirmed_unavailable_distribution": dict(
            Counter(e["first_confirmed_unavailable_stage"] for e in events)
        ),
        "presentation_counts": {
            "specific": 0,
            "broad_group": 0,
            "generic": sum(e["presentation"] == "Object." for e in events),
            "unknown": sum(e["presentation"] != "Object." for e in events),
        },
        "after_counts": None,
        "limitations": [
            "Missing evidence is UNKNOWN, not inferred instability or expiry",
            "New screening predictions never substitute for original runtime observations",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--population", type=Path, default=Path("benchmark-results/v02/populations-02.json")
    )
    parser.add_argument(
        "--trace",
        type=Path,
        default=Path("benchmark-results/v0-rescue/realtime-06-gpu-no-depth/updates.jsonl"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(json.loads(args.population.read_text()), args.trace)
    result["population_sha256"] = digest(args.population)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "events"}))


if __name__ == "__main__":
    main()
