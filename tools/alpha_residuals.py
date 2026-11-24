"""Extract generic delivered outputs using immutable lineage, never proximity joins."""

import argparse
import hashlib
import json
import os
from pathlib import Path


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def semantic_blockers(state, now):
    """Identify sufficient blocking conditions, not guessed counterfactual causes."""
    from perception_lab.config import canonical_hash
    from perception_lab.track_semantics import SemanticFusionConfig

    policy = SemanticFusionConfig()
    expected = canonical_hash(
        {"policy_version": "bounded-track-semantics-v2", "config": policy.model_dump()}
    )
    if not state or state.get("configuration_hash") != expected or now is None:
        return {"policy_verified": False, "blockers": ["UNKNOWN"]}
    if "evidence" not in state:
        # Full stage traces also omit repeated history. Its count can prove too
        # little support, but cannot establish scores or per-configuration causes.
        count = state.get("evidence_count")
        blockers = []
        if state.get("quality") == "EXPIRED":
            blockers.append("EXPIRED")
        if len(state.get("providers", [])) > 1:
            blockers.append("PROVIDER_STREAM_SPLIT")
        if type(count) is int and 0 < count < policy.minimum_support:
            blockers.append("INSUFFICIENT_DETECTOR_UPDATES")
        return {
            "policy_verified": True,
            "configuration_hash": expected,
            "recent_evidence_count": count,
            "blockers": blockers or ["UNKNOWN"],
            "limitation": "History omitted; scores/configuration splits cannot be reconstructed",
        }
    recent = [
        e["observation"]
        for e in state.get("evidence", [])
        if 0 <= now - e["observation"]["source_frame"]["observation_ns"] < policy.expiry_ns
    ]
    providers = {e["provider_id"] for e in recent}
    configurations = {
        (e["provider_id"], e["model_version"], e.get("provider_configuration_sha256"))
        for e in recent
    }
    frames = {json.dumps(e["source_frame"], sort_keys=True) for e in recent}
    concepts = [e["concept"] for e in recent if e.get("concept")]
    blockers = []
    if state.get("quality") == "EXPIRED":
        blockers.append("EXPIRED")
    if len(providers) > 1:
        blockers.append("PROVIDER_STREAM_SPLIT")
    if len(configurations) > len(providers):
        blockers.append("CONFIG_STREAM_SPLIT")
    if recent and len(frames) < policy.minimum_support:
        blockers.append("INSUFFICIENT_DETECTOR_UPDATES")
    if concepts and all(c["confidence"] < policy.minimum_confidence for c in concepts):
        blockers.append("BELOW_SCORE_SUPPORT")
    return {
        "policy_verified": True,
        "configuration_hash": expected,
        "recent_evidence_count": len(recent),
        "distinct_source_frames": len(frames),
        "blockers": blockers or ["UNKNOWN"],
        "scope": "Sufficient observed fusion blockers; not exhaustive causal attribution",
    }


def collect(rows):
    contexts, delivered, targets = {}, set(), []
    for row in rows:
        if row.get("schema_version") != 2 or row.get("trace_mode", "FULL") != "FULL":
            raise ValueError("Residual extraction requires full schema-2 traces")
        entities = (row.get("world") or {}).get("entities", [])
        for decision in (row.get("attention_decision_set") or {}).get("selected", []):
            lineage = decision.get("lineage")
            if not lineage or not lineage.get("attention_event_id"):
                continue
            matches = [e for e in entities if e["entity_id"] == decision["entity_id"]]
            if len(matches) != 1:
                raise ValueError("Selected event lacks one exact world entity")
            entity = matches[0]
            if entity["entity_id"] != lineage.get("entity_instance_id"):
                raise ValueError("Selected entity disagrees with immutable lineage")
            observation = entity.get("entity_observation")
            if observation is not None and (
                observation["observation_id"] != lineage["observation_id"]
                or observation["source_frame"] != lineage["origin_source_identity"]
            ):
                raise ValueError("Observation and immutable lineage disagree")
            context = {
                "lineage": lineage,
                "source_observation": observation,
                "semantic_state": entity.get("track_semantics"),
                "authorization": decision.get("semantic_authorization_reason"),
                "event_timestamp_ns": decision.get("state_timestamp"),
            }
            key = lineage["attention_event_id"]
            if key in contexts and contexts[key] != context:
                raise ValueError("Ambiguous attention event context")
            contexts[key] = context
            if len(contexts) > 10_000:
                raise ValueError("Event context capacity exceeded")
        for output in (row.get("alert_output_set") or {}).get("outputs", []):
            if not output.get("delivered"):
                continue
            intent, presentation = output["intent"], output["presentation"]
            alert_id = intent["alert_id"]
            if alert_id in delivered:
                raise ValueError("Duplicate delivered alert")
            delivered.add(alert_id)
            lineage = intent.get("lineage")
            if not lineage or presentation.get("lineage") != lineage:
                raise ValueError("Delivered output lacks matching immutable lineage")
            context = contexts.get(lineage["attention_event_id"])
            if context is None or context["lineage"] != lineage:
                raise ValueError("No exact causal event context for delivered output")
            if intent["entity_id"] != lineage["entity_instance_id"]:
                raise ValueError("Intent entity disagrees with lineage")
            if presentation.get("semantic_level") != "GENERIC":
                continue
            observation = context["source_observation"]
            targets.append(
                {
                    "alert_id": alert_id,
                    **context,
                    "association": "EXACT_IMMUTABLE_EVENT_LINEAGE",
                    "reason": "GENERIC_PRESENTATION",
                    "screenable": observation is not None,
                    "screening_exclusion": None
                    if observation
                    else "SOURCE_OBSERVATION_UNAVAILABLE",
                    "intent_reasons": intent.get("reason_codes", []),
                    "first_later_specific_stable_ns": None,
                    "first_later_group_stable_ns": None,
                }
            )
        now = (row.get("identity") or {}).get("observation_ns")
        if now is not None:
            by_id = {json.dumps(e["entity_id"], sort_keys=True): e for e in entities}
            for target in targets:
                event_time = target["event_timestamp_ns"]
                if event_time is None or now <= event_time:
                    continue
                entity = by_id.get(
                    json.dumps(target["lineage"]["entity_instance_id"], sort_keys=True)
                )
                semantics = (entity or {}).get("track_semantics") or {}
                for kind, quality, expiry in (
                    ("specific", "quality", "valid_until_ns"),
                    ("group", "group_quality", "group_valid_until_ns"),
                ):
                    key = "first_later_" + kind + "_stable_ns"
                    if (
                        target[key] is None
                        and semantics.get(quality) == "STABLE"
                        and semantics.get(expiry) is not None
                        and now < semantics[expiry]
                    ):
                        target[key] = now
    for target in targets:
        semantics = target["semantic_state"] or {}
        target["fusion_diagnostics"] = semantic_blockers(semantics, target["event_timestamp_ns"])
        later_stable = (
            target["first_later_specific_stable_ns"] is not None
            or target["first_later_group_stable_ns"] is not None
        )
        target["temporal_classification"] = (
            "BECAME_STABLE_CONTINUOUSLY"
            if later_stable
            else "SPECIFIC_UNSTABLE_GROUP_STABLE"
            if semantics.get("quality") != "STABLE"
            and semantics.get("group_quality") == "STABLE"
            and target["event_timestamp_ns"] is not None
            and semantics.get("group_valid_until_ns") is not None
            and target["event_timestamp_ns"] < semantics["group_valid_until_ns"]
            else target["fusion_diagnostics"]["blockers"][0]
        )
        # Later recovery is not a retroactive correction of the generic output.
        # Candidate screening remains tied to its unresolved original source frame.
    return {
        "delivered_outputs": len(delivered),
        "delivered_lineages_verified": len(delivered),
        "generic_outputs": len(targets),
        "targets": targets,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = json.loads((args.run / "continuous-summary.json").read_text())
    if (
        summary["status"] != "COMPLETE_CONTINUOUS_OFFLINE_PRESENTATION_ABLATION"
        or summary["arm"] != "B"
    ):
        raise ValueError("Complete continuous B run required")
    trace = args.run / "updates.jsonl"
    trace_hash = digest(trace)
    if trace_hash != summary["updates_sha256"]:
        raise ValueError("Trace hash mismatch")
    with trace.open() as stream:
        report = collect(json.loads(line) for line in stream)
    report.update(
        schema_version=1,
        status="EXACT_LINEAGE_RESIDUAL_SCREENING_SET",
        source_sha256=summary["source_sha256"],
        trace_sha256=trace_hash,
        analyzer_sha256=digest(Path(__file__)),
        scope="Generic outputs of this run only; not historical correspondence or accuracy",
    )
    # Publish only a complete file, without replacing an existing evidence artifact.
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    try:
        os.link(temporary, args.output)
    finally:
        temporary.unlink()
    print(json.dumps({k: v for k, v in report.items() if k != "targets"}))


if __name__ == "__main__":
    main()
