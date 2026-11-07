"""Compact Alpha diagnostics: explicit current-state fields, no history payloads."""

from dataclasses import fields, is_dataclass

FIELDS = {
    "TrackSnapshot": {
        "track_id",
        "lifecycle",
        "observation_status",
        "bbox",
        "latest_observed_ns",
        "state_ns",
        "quality",
        "entity_observation",
        "latest_failure",
    },
    "PredictedTrajectory": {
        "trajectory_id",
        "entity_id",
        "source_state_timestamp",
        "prediction_start_timestamp",
        "coordinate_space",
        "frame_id",
        "units",
        "origin",
        "velocity",
        "velocity_status",
        "quality",
        "reasons",
        "physical_status",
    },
    "EntityInteractionForecast": {
        "entity_id",
        "trajectory_id",
        "state_timestamp",
        "interaction_type",
        "current_corridor_relation",
        "predicted_corridor_relation",
        "quality",
        "physical_validity",
        "reasons",
        "crossing_direction",
        "reference_type",
    },
    "RiskAssessment": {
        "entity_id",
        "state_timestamp",
        "valid_until_ns",
        "risk_level",
        "evidence_quality",
        "reason_codes",
        "trend",
        "physical_validity",
    },
    "EntityCorridorRelation": {
        "entity_id",
        "state_timestamp",
        "relation",
        "coordinate_basis",
        "quality",
        "forward_distance_m",
        "lateral_offset_m",
    },
    "AttentionDecision": {
        "state_timestamp",
        "entity_id",
        "decision",
        "priority",
        "reason_codes",
        "cooldown_active",
        "event",
        "source_observation_ns",
        "physical_validity",
        "semantic_authorization_reason",
        "lineage",
    },
}
OMIT = {
    "history",
    "evidence",
    "provenance",
    "position_sources",
    "samples",
    "regions",
    "projected_ground",
    "hypotheses",
    "risk_provenance",
    "world_provenance",
    "corridor_provenance",
    "trajectory_provenance",
}


def compact_alpha(value, *, full_observation=False):
    """Build small records directly; never first serialize a complete debug payload."""
    if is_dataclass(value):
        kind = type(value).__name__
        if kind == "PerceivedEntityObservation" and not full_observation:
            return {
                "observation_id": value.observation_id,
                "source_frame": compact_alpha(value.source_frame),
            }
        selected = FIELDS.get(kind)
        record = {
            f.name: compact_alpha(getattr(value, f.name), full_observation=kind == "Detection")
            for f in fields(value)
            if f.name not in OMIT and (selected is None or f.name in selected)
        }
        if kind == "TrackSemanticState":
            record["evidence_count"] = len(value.evidence)
        return record
    if isinstance(value, (tuple, list)):
        return [compact_alpha(v) for v in value]
    if isinstance(value, dict):
        return {k: compact_alpha(v) for k, v in value.items()}
    return value
