"""Immutable neutral interaction evidence. No risk or attention policy."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .contracts import ComponentProvenance
from .corridor_types import CorridorAnalysis
from .trajectory_types import TrajectorySet
from .world_types import WorldEntityId, WorldState


class InteractionLevel(StrEnum):
    IMAGE = "IMAGE_GEOMETRIC"
    BEARING = "BEARING_GEOMETRIC"
    WORLD = "WORLD_RESEARCH_UNVALIDATED"
    PHYSICAL = "PHYSICAL_METRIC_VALIDATED"  # Reserved; current analyzer never promotes inputs.


@dataclass(frozen=True)
class ReferenceMotion:
    session_id: str
    state_timestamp: int
    frame_id: str
    position: tuple[float, float, float]
    velocity: tuple[float, float, float]
    reference_type: str
    validation_status: str
    quality: str
    provenance: tuple[ComponentProvenance, ...]
    units: str = "meters"
    velocity_units: str = "meters/second"


@dataclass(frozen=True)
class RelativeMotionValues:
    separation_meters: float
    closing_speed_mps: float | None
    ttc_seconds: float | None
    cpa_seconds: float | None
    cpa_distance_meters: float | None
    stationary: bool


@dataclass(frozen=True)
class TimeToContactCandidate:
    status: str
    seconds: float | None
    closing_speed_mps: float | None
    reference_type: str
    physical_validity: InteractionLevel
    quality: str
    relative_position_source: str
    relative_velocity_source: str
    assumptions: tuple[str, ...]
    provenance: tuple[ComponentProvenance, ...]
    physical_validation: str = "NO"


@dataclass(frozen=True)
class ClosestApproachCandidate:
    status: str
    time_seconds: float | None
    distance_meters: float | None
    current_separation_meters: float | None
    reference_type: str
    physical_validity: InteractionLevel
    quality: str
    relative_position_source: str
    relative_velocity_source: str
    assumptions: tuple[str, ...]
    provenance: tuple[ComponentProvenance, ...]
    physical_validation: str = "NO"


@dataclass(frozen=True)
class InteractionSample:
    horizon_ns: int
    position: tuple[float, ...]
    corridor_relation: str
    distance_to_corridor: float
    quality: str


@dataclass(frozen=True)
class CorridorClosestApproach:
    distance: float
    horizon_ns: int
    coordinate_frame: str
    units: str
    physical_validity: InteractionLevel
    quality: str


@dataclass(frozen=True)
class ApproachEvidence:
    state: str
    reference_type: str
    coordinate_frame: str
    units: str
    initial_distance: float | None
    final_distance: float | None
    quality: str


@dataclass(frozen=True)
class EntityInteractionForecast:
    entity_id: WorldEntityId
    trajectory_id: str
    state_timestamp: int
    horizon_ns: int
    current_corridor_relation: str
    predicted_corridor_relation: str
    interaction_type: str
    intersection_intervals_ns: tuple[tuple[int, int], ...]
    predicted_corridor_entry_time_ns: int | None
    predicted_corridor_exit_time_ns: int | None
    earliest_possible_entry_ns: int | None
    latest_possible_entry_ns: int | None
    envelope_interaction: str
    closest_corridor_approach: CorridorClosestApproach | None
    approach_evidence: ApproachEvidence
    samples: tuple[InteractionSample, ...]
    ttc: TimeToContactCandidate
    cpa: ClosestApproachCandidate
    physical_validity: InteractionLevel
    quality: str
    reasons: tuple[str, ...]
    source_ages: tuple[tuple[str, int | None], ...]
    assumptions: tuple[str, ...]
    provenance: tuple[ComponentProvenance, ...]
    diagnostics: tuple[str, ...]
    crossing_direction: str = "UNKNOWN"
    longitudinal_relation: str = "UNKNOWN"
    reference_type: str = "CURRENT_FROZEN_CORRIDOR"


@dataclass(frozen=True)
class InteractionAnalysis:
    session_id: str
    state_timestamp: int
    entity_interactions: tuple[EntityInteractionForecast, ...]
    corridor_provenance: ComponentProvenance
    trajectory_provenance: ComponentProvenance
    world_provenance: ComponentProvenance
    provenance: ComponentProvenance
    quality: str
    diagnostics: tuple[str, ...]
    unavailable: tuple[tuple[WorldEntityId, str], ...]
    schema_version: int = 1


class InteractionAnalyzer(Protocol):
    def analyze(
        self,
        state: WorldState,
        corridor: CorridorAnalysis,
        trajectories: TrajectorySet,
        reference: ReferenceMotion | None = None,
    ) -> InteractionAnalysis: ...
