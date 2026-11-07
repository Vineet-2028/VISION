"""Immutable modality-independent interruption intents; no speech or safety verdict."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .contracts import ComponentProvenance
from .event_lineage import EventLineage
from .perceived_entity import SemanticConcept
from .risk_types import RiskAssessmentSet, RiskLevel, RiskQuality, RiskTrend
from .world_types import WorldEntityId


class AttentionAction(StrEnum):
    SILENT = "SILENT"
    ANNOUNCE = "ANNOUNCE"
    REPEAT = "REPEAT"
    ESCALATE = "ESCALATE"


@dataclass(frozen=True)
class AudioChannelState:
    busy: bool = False
    active_priority: int = 0


@dataclass(frozen=True)
class AttentionEvent:
    event_id: str
    episode_id: str
    kind: str
    created_ns: int
    valid_until_ns: int


@dataclass(frozen=True)
class AttentionSemanticEvidence:
    """Optional upstream authorization, never inferred by a renderer.

    Existing policies leave this absent. Future producers must identify the same
    entity/session and retain evidence freshness and quality for each supplied fact.
    """

    entity_id: WorldEntityId
    observed_ns: int
    valid_until_ns: int
    category: str | None = None
    direction: str | None = None
    interaction: str | None = None
    quality: str = "UNAVAILABLE"
    provenance: tuple[ComponentProvenance, ...] = ()
    concept: SemanticConcept | None = None
    group_spoken_label: str | None = None
    semantic_level: str = "UNAVAILABLE"


@dataclass(frozen=True)
class AttentionDecision:
    state_timestamp: int
    entity_id: WorldEntityId | None
    decision: AttentionAction
    priority: int
    source_risk_level: RiskLevel | None
    source_risk_quality: RiskQuality | None
    risk_trend: RiskTrend
    reason_codes: tuple[str, ...]
    novelty: str
    cooldown_active: bool
    repeat_count: int
    escalation: bool
    quality: str
    event: AttentionEvent | None
    interaction_reasons: tuple[str, ...]
    provenance: ComponentProvenance
    config_hash: str
    category: str | None = None
    direction: str | None = None
    semantic_evidence: AttentionSemanticEvidence | None = None
    source_observation_ns: int | None = None
    source_age_basis: str = "UNAVAILABLE"
    physical_validity: str = "UNVALIDATED"
    semantic_authorization_reason: str = "NOT_EVALUATED"
    lineage: EventLineage | None = None


@dataclass(frozen=True)
class SuppressedAttentionCandidate:
    decision: AttentionDecision
    reason: str


@dataclass(frozen=True)
class AttentionDecisionSet:
    session_id: str
    state_timestamp: int
    valid_until_ns: int
    selected: tuple[AttentionDecision, ...]
    suppressed: tuple[SuppressedAttentionCandidate, ...]
    scene_status: str
    reason_summaries: tuple[str, ...]
    provenance: ComponentProvenance
    config_hash: str
    risk_provenance: ComponentProvenance
    upstream_coverage: str
    schema_version: int = 1


class AttentionEngine(Protocol):
    def decide(
        self,
        risk: RiskAssessmentSet,
        audio: AudioChannelState | None = None,
        *,
        now_ns: int | None = None,
    ) -> AttentionDecisionSet: ...

    def reset(self) -> None: ...
