"""Immutable links to records actually consumed in one Guardian update.

Record identities are not physical ground-truth event identities. Never infer
cross-run or historical correspondence from these links, timestamps or boxes.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .attention_types import AttentionDecision, AttentionDecisionSet
    from .contracts import FrameIdentity, FrameResult
    from .tracking_types import TrackId
    from .world_types import WorldEntityId


@dataclass(frozen=True)
class EventLineage:
    entity_instance_id: WorldEntityId
    track_id: TrackId
    track_generation: int
    observation_id: str | None
    origin_source_identity: FrameIdentity | None
    world_record_id: str
    interaction_record_id: str | None
    risk_record_id: str | None
    attention_event_id: str | None
    attention_episode_id: str | None
    missing_links: tuple[str, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            self.entity_instance_id.session_id != self.track_id.session_id
            or self.track_generation != self.track_id.serial
        ):
            raise ValueError("Lineage session/generation mismatch")
        if (self.observation_id is None) != (self.origin_source_identity is None):
            raise ValueError("Lineage observation identity must be complete or unavailable")


def attach_event_lineage(result: FrameResult) -> AttentionDecisionSet:
    """Link by exact IDs within the actual update, never by proximity or overlap."""
    decisions = result.attention_decision_set
    if decisions is None:
        raise ValueError("Lineage requires an attention decision set")
    state = result.world_state
    if state is None:
        return decisions
    if (
        state.session_id != decisions.session_id
        or state.state_timestamp != result.identity.observation_ns
        or decisions.state_timestamp < state.state_timestamp
    ):
        raise ValueError("Lineage world/attention session mismatch")
    for batch in (result.interaction_analysis, result.risk_assessment_set):
        if batch is not None and batch.session_id != state.session_id:
            raise ValueError("Lineage upstream session mismatch")
    entities = {e.entity_id: e for e in state.entities}
    interactions = (
        {i.entity_id: i for i in result.interaction_analysis.entity_interactions}
        if result.interaction_analysis is not None
        else {}
    )
    risks = (
        {r.entity_id: r for r in result.risk_assessment_set.assessments}
        if result.risk_assessment_set is not None
        else {}
    )
    if (
        len(entities) != len(state.entities)
        or result.interaction_analysis is not None
        and len(interactions) != len(result.interaction_analysis.entity_interactions)
        or result.risk_assessment_set is not None
        and len(risks) != len(result.risk_assessment_set.assessments)
    ):
        raise ValueError("Ambiguous duplicate lineage record")

    def attach(decision: AttentionDecision) -> AttentionDecision:
        entity = entities.get(decision.entity_id) if decision.entity_id is not None else None
        if entity is None:
            return decision
        interaction = interactions.get(entity.entity_id)
        risk = risks.get(entity.entity_id)
        observation = entity.entity_observation
        if observation is not None and (
            observation.source_frame.source_id != result.identity.source_id
            or observation.source_frame.timing != result.identity.timing
            or observation.source_frame.sequence > result.identity.sequence
            or observation.source_frame.observation_ns != entity.latest_observed_ns
            or observation.source_frame.observation_ns > state.state_timestamp
        ):
            raise ValueError("Lineage observation source/time mismatch")
        if any(
            record is not None and record.state_timestamp > decision.state_timestamp
            for record in (interaction, risk)
        ):
            raise ValueError("Lineage upstream record is from the future")
        prefix = f"{state.session_id}:{entity.entity_id.serial}"
        missing = []
        if observation is None:
            missing.append("ENTITY_OBSERVATION_UNAVAILABLE")
        if interaction is None:
            missing.append("INTERACTION_RECORD_UNAVAILABLE")
        if risk is None:
            missing.append("RISK_RECORD_UNAVAILABLE")
        if decision.event is None:
            missing.append("ATTENTION_EVENT_UNAVAILABLE")
        return replace(
            decision,
            lineage=EventLineage(
                entity.entity_id,
                entity.source_track_id,
                entity.source_track_id.serial,
                observation.observation_id if observation else None,
                observation.source_frame if observation else None,
                f"{prefix}:world:{state.state_timestamp}",
                f"{prefix}:interaction:{interaction.state_timestamp}:{interaction.trajectory_id}"
                if interaction
                else None,
                f"{prefix}:risk:{risk.state_timestamp}" if risk else None,
                decision.event.event_id if decision.event else None,
                decision.event.episode_id if decision.event else None,
                tuple(missing),
            ),
        )

    return replace(
        decisions,
        selected=tuple(attach(d) for d in decisions.selected),
        suppressed=tuple(replace(s, decision=attach(s.decision)) for s in decisions.suppressed),
    )
