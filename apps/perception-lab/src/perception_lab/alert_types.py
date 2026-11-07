"""Immutable alert contracts. No platform audio, model objects or navigation."""

from dataclasses import dataclass
from typing import Literal, Protocol

from .attention_types import AttentionAction, AudioChannelState
from .contracts import ComponentProvenance
from .event_lineage import EventLineage
from .world_types import WorldEntityId

Category = Literal["PERSON", "BICYCLE", "MOTORCYCLE", "VEHICLE", "OBSTACLE", "UNKNOWN"]
Direction = Literal["LEFT", "RIGHT", "AHEAD", "UNKNOWN"]
Interaction = Literal["CROSSING", "APPROACHING", "IN_CORRIDOR", "STATIC_OBSTACLE", "GENERIC"]


@dataclass(frozen=True)
class AlertIntent:
    alert_id: str
    event_id: str
    episode_id: str
    session_id: str
    state_timestamp: int
    source_observation_ns: int | None
    entity_id: WorldEntityId | None
    decision_type: AttentionAction
    category: Category
    direction: Direction
    interaction: Interaction
    urgency: int
    risk_level: str | None
    evidence_quality: str
    physical_validity: str
    valid_until_ns: int
    reason_codes: tuple[str, ...]
    provenance: tuple[ComponentProvenance, ...]
    config_hash: str
    source_age_basis: str
    presentation_constraints: tuple[str, ...] = ("NO_NAVIGATION", "NO_PHYSICAL_PRECISION")
    concept_text: str | None = None
    semantic_level: str = "GENERIC"
    lineage: EventLineage | None = None

    def __post_init__(self) -> None:
        if self.lineage is not None and (
            self.lineage.entity_instance_id != self.entity_id
            or self.lineage.attention_event_id != self.event_id
            or self.lineage.attention_episode_id != self.episode_id
        ):
            raise ValueError("Alert intent lineage mismatch")


@dataclass(frozen=True)
class AlertPresentation:
    alert_id: str
    speech_text: str
    short_text: str
    presentation_priority: int
    style: str
    modality_recommendation: tuple[str, ...]
    source_timestamp: int | None
    attention_timestamp: int
    generation_timestamp: int
    source_age_ns: int | None
    attention_age_ns: int
    valid_until_ns: int
    quality: str
    timing_status: str
    word_count: int
    character_count: int
    estimated_speech_seconds: float
    provenance: ComponentProvenance
    semantic_level: str = "GENERIC"
    lineage: EventLineage | None = None


@dataclass(frozen=True)
class AlertOutput:
    status: str
    reason: str
    intent: AlertIntent | None = None
    presentation: AlertPresentation | None = None
    delivered: bool = False  # Text sink acceptance, never proof of speech heard.
    delivery_timestamp: int | None = None
    source_age_at_delivery_ns: int | None = None
    presentation_age_ns: int | None = None
    superseded_alert_id: str | None = None


@dataclass(frozen=True)
class AlertOutputSet:
    session_id: str
    state_timestamp: int
    mode: str
    outputs: tuple[AlertOutput, ...]
    upstream_expired_candidates: int
    provenance: ComponentProvenance
    schema_version: int = 1


class AlertRenderer(Protocol):
    def render(self, intent: AlertIntent, now_ns: int) -> AlertPresentation: ...


class AlertPresenter(Protocol):
    """Single-owner, bounded, nonblocking. Recheck deadline at actual consumption."""

    def submit(
        self, intent: AlertIntent, presentation: AlertPresentation, now_ns: int
    ) -> AlertOutput: ...
    def reset(self, session_id: str | None = None) -> None: ...
    def channel_state(self) -> AudioChannelState: ...
