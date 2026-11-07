"""Immutable risk evidence boundary. No alert, navigation or attention decision."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .contracts import ComponentProvenance
from .corridor_types import CorridorAnalysis
from .interaction_types import InteractionAnalysis, InteractionLevel
from .trajectory_types import TrajectorySet
from .world_types import Capability, WorldEntityId, WorldState


class RiskLevel(StrEnum):
    UNDETERMINED = "UNDETERMINED"
    LOW = "LOW"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    SEVERE = "SEVERE"  # Reserved; this unvalidated baseline never emits SEVERE.


class RiskQuality(StrEnum):
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    INSUFFICIENT = "INSUFFICIENT"


class RiskTrend(StrEnum):
    RISING = "RISING"
    STABLE = "STABLE"
    FALLING = "FALLING"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RiskFactor:
    code: str
    effect: str  # SUPPORTING, REDUCING or DIAGNOSTIC, never probability.
    source: str
    value: str


@dataclass(frozen=True)
class RiskAssessment:
    entity_id: WorldEntityId
    state_timestamp: int
    valid_until_ns: int
    risk_level: RiskLevel
    evidence_quality: RiskQuality
    risk_factors: tuple[RiskFactor, ...]
    reducing_factors: tuple[RiskFactor, ...]
    interaction_status: tuple[str, ...]
    physical_validity: InteractionLevel | None
    source_ages: tuple[tuple[str, int | None], ...]
    reason_codes: tuple[str, ...]
    trend: RiskTrend
    provenance: tuple[ComponentProvenance, ...]
    config_hash: str
    semantic_validation: str
    research_score: float | None = None
    physical_risk_validated: bool = False


@dataclass(frozen=True)
class RiskAssessmentSet:
    session_id: str
    state_timestamp: int
    valid_until_ns: int
    assessments: tuple[RiskAssessment, ...]
    ranking: tuple[WorldEntityId, ...]
    counts: tuple[tuple[RiskLevel, int], ...]
    diagnostics: tuple[str, ...]
    capabilities: tuple[Capability, ...]
    provenance: ComponentProvenance
    config_hash: str
    world_provenance: ComponentProvenance
    upstream_coverage: str = "UPSTREAM_INTERACTION_COVERAGE: UNVALIDATED; TASK014_PROXY_RECALL=5.8%"
    schema_version: int = 1


class RiskEngine(Protocol):
    def assess(
        self,
        state: WorldState,
        corridor: CorridorAnalysis | None,
        trajectories: TrajectorySet | None,
        interaction: InteractionAnalysis | None,
    ) -> RiskAssessmentSet: ...

    def reset(self) -> None: ...
