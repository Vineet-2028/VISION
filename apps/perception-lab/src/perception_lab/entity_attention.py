"""Attach fresh stable entity semantics without changing interruption decisions."""

from dataclasses import replace

from .attention_types import AttentionDecision, AttentionDecisionSet, AttentionSemanticEvidence
from .contracts import ComponentProvenance
from .world_types import WorldState


def attach_entity_semantics(
    decisions: AttentionDecisionSet, state: WorldState
) -> AttentionDecisionSet:
    if (
        decisions.session_id != state.session_id
        or decisions.state_timestamp < state.state_timestamp
    ):
        raise ValueError("Attention/world association mismatch")
    entities = {entity.entity_id: entity for entity in state.entities}

    def attach(decision: AttentionDecision) -> AttentionDecision:
        entity = entities.get(decision.entity_id) if decision.entity_id is not None else None
        semantics = entity.track_semantics if entity is not None else None
        reason = (
            "TRACK_NOT_ASSOCIATED"
            if entity is None
            else "TRACK_REPLACED"
            if entity.lifecycle.value == "LOST"
            else "NO_TRACK_SEMANTIC_EVIDENCE"
            if semantics is None
            else "TRACK_REPLACED"
            if semantics.track_id != entity.source_track_id
            else "SEMANTIC_EXPIRED"
            if semantics.quality == "EXPIRED"
            else "SEMANTIC_UNSTABLE"
            if semantics.quality != "STABLE"
            else "NO_AUTHORIZED_CONCEPT"
            if semantics.selected_concept is None
            else "SEMANTIC_TIME_UNAVAILABLE"
            if semantics.last_observed_ns is None or semantics.valid_until_ns is None
            else "SEMANTIC_FROM_FUTURE"
            if decision.state_timestamp < semantics.last_observed_ns
            else "SEMANTIC_EXPIRED"
            if decision.state_timestamp >= semantics.valid_until_ns
            else "AUTHORIZED_STABLE_SPECIFIC"
        )
        if reason != "AUTHORIZED_STABLE_SPECIFIC":
            if (
                entity is not None
                and entity.lifecycle.value != "LOST"
                and semantics is not None
                and semantics.track_id == entity.source_track_id
                and semantics.group_quality == "STABLE"
                and semantics.group_spoken_label is not None
                and semantics.group_last_observed_ns is not None
                and semantics.group_valid_until_ns is not None
                and semantics.group_last_observed_ns
                <= decision.state_timestamp
                < semantics.group_valid_until_ns
            ):
                return replace(
                    decision,
                    semantic_authorization_reason="AUTHORIZED_STABLE_GROUP",
                    semantic_evidence=AttentionSemanticEvidence(
                        entity.entity_id,
                        semantics.group_last_observed_ns,
                        semantics.group_valid_until_ns,
                        quality="GOOD",
                        provenance=(
                            ComponentProvenance(
                                "track-semantic-fusion-v2",
                                "entity-semantics",
                                configuration_hash=semantics.configuration_hash,
                            ),
                        ),
                        group_spoken_label=semantics.group_spoken_label,
                        semantic_level="GROUP",
                    ),
                )
            return replace(decision, semantic_authorization_reason=reason)
        assert semantics is not None
        assert entity is not None
        assert semantics.last_observed_ns is not None and semantics.valid_until_ns is not None
        return replace(
            decision,
            semantic_authorization_reason=reason,
            semantic_evidence=AttentionSemanticEvidence(
                entity.entity_id,
                semantics.last_observed_ns,
                semantics.valid_until_ns,
                quality="GOOD",
                provenance=(
                    ComponentProvenance(
                        "track-semantic-fusion-v2",
                        "entity-semantics",
                        configuration_hash=semantics.configuration_hash,
                    ),
                ),
                concept=semantics.selected_concept,
                semantic_level="SPECIFIC",
            ),
        )

    return replace(
        decisions,
        selected=tuple(attach(d) for d in decisions.selected),
        suppressed=tuple(replace(s, decision=attach(s.decision)) for s in decisions.suppressed),
    )
