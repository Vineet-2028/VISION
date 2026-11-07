"""Immutable downstream prediction evidence. Never observations or risk decisions."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .contracts import ComponentProvenance, FrameIdentity
from .corridor_types import CorridorAnalysis
from .world_types import WorldEntityId, WorldState


class TrajectoryDomain(StrEnum):
    IMAGE = "IMAGE_SPACE"
    BEARING = "CAMERA_BEARING_SPACE"
    WORLD = "LOCAL_WORLD_RESEARCH"


class TrajectoryPhysicalStatus(StrEnum):
    IMAGE_ONLY = "IMAGE_ONLY"
    CAMERA_RELATIVE = "CAMERA_RELATIVE"
    WORLD_RESEARCH_UNVALIDATED = "WORLD_RESEARCH_UNVALIDATED"
    PHYSICAL_METRIC_VALIDATED = "PHYSICAL_METRIC_VALIDATED"


@dataclass(frozen=True)
class TrajectorySample:
    horizon_ns: int
    timestamp_ns: int
    position: tuple[float, ...]
    envelope_radius: float
    quality: str


@dataclass(frozen=True)
class PredictedTrajectory:
    trajectory_id: str
    entity_id: WorldEntityId
    source_state_timestamp: int
    prediction_start_timestamp: int
    coordinate_space: TrajectoryDomain
    frame_id: str
    units: str
    model: str
    physical_status: TrajectoryPhysicalStatus
    origin: tuple[float, ...]
    velocity: tuple[float, ...]
    velocity_status: str
    samples: tuple[TrajectorySample, ...]
    quality: str
    reasons: tuple[str, ...]
    source_observations: tuple[FrameIdentity, ...]
    source_observation_count: int
    history_span_ns: int
    fit_residual: float
    rejected_observations: int
    provenance: tuple[ComponentProvenance, ...]
    config_hash: str
    uncertainty_status: str = "UNCALIBRATED_RESEARCH_ENVELOPE"
    motion_basis: str = "OBSERVED_HISTORY"


@dataclass(frozen=True)
class TrajectoryCorridorRelation:
    entity_id: WorldEntityId
    trajectory_id: str
    current_relation: str
    future_relations: tuple[tuple[int, str], ...]
    predicted_corridor_entry_time_ns: int | None
    quality: str
    coordinate_basis: str
    limitation: str = "FROZEN_CURRENT_CORRIDOR; POINT_PATH_ONLY; NOT_TTC"


@dataclass(frozen=True)
class TrajectorySet:
    session_id: str
    state_timestamp: int
    trajectories: tuple[PredictedTrajectory, ...]
    preferred_trajectory_ids: tuple[str, ...]
    corridor_relations: tuple[TrajectoryCorridorRelation, ...]
    unavailable: tuple[tuple[WorldEntityId, str], ...]
    provenance: ComponentProvenance
    world_provenance: ComponentProvenance
    diagnostics: tuple[str, ...]
    schema_version: int = 1


class TrajectoryPredictor(Protocol):
    def predict(
        self, state: WorldState, corridor: CorridorAnalysis | None = None
    ) -> TrajectorySet: ...
