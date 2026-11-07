"""Immutable derived relevance evidence. No safety, navigation or risk policy."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .contracts import ComponentProvenance
from .world_types import EvidenceSource, WorldEntityId, WorldState

Point2 = tuple[float, float]
Point3 = tuple[float, float, float]


class CorridorMode(StrEnum):
    IMAGE = "IMAGE_SPACE_CORRIDOR"
    GROUND = "GROUND_PLANE_CORRIDOR"
    WORLD = "WORLD_SPACE_CORRIDOR"


class Relation(StrEnum):
    INSIDE = "INSIDE"
    INTERSECTS = "INTERSECTS"
    NEAR_BOUNDARY = "NEAR_BOUNDARY"
    OUTSIDE = "OUTSIDE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class InteractionZone:
    zone_id: str
    kind: str
    coordinate_frame: str
    polygon: tuple[Point3, ...]


@dataclass(frozen=True)
class UserCorridorState:
    state_timestamp: int
    mode: CorridorMode
    zone: InteractionZone
    image_polygon: tuple[Point2, ...]
    origin: Point3 | None
    forward: Point3 | None
    lateral: Point3 | None
    near_distance_m: float | None
    far_distance_m: float | None
    near_half_width_m: float | None
    far_half_width_m: float | None
    heading_source: str
    heading_evidence: EvidenceSource
    ground_evidence: EvidenceSource | None
    quality: str
    reasons: tuple[str, ...]
    observed_fraction: float | None = None


# The corridor itself is the immutable state at the explicit source timestamp.
UserCorridor = UserCorridorState


@dataclass(frozen=True)
class EntityCorridorRelation:
    entity_id: WorldEntityId
    state_timestamp: int
    relation: Relation
    coordinate_basis: str
    representative_source: str
    forward_distance_m: float | None
    lateral_offset_m: float | None
    signed_boundary_distance_m: float | None
    quality: str
    sources: tuple[EvidenceSource, ...]
    assumptions: tuple[str, ...]


@dataclass(frozen=True)
class CorridorSurfaceEvidence:
    state_timestamp: int
    corridor_id: str
    candidate_ground_fraction: float | None
    candidate_traversable_fraction: float | None
    obstacle_evidence_fraction: float | None
    unknown_fraction: float
    sample_count: int
    source: EvidenceSource
    quality: str
    validation_status: str = "UNVERIFIED"
    basis: str = "IMAGE_POINT_SAMPLES; NOT_AREA_OR_METRIC_COVERAGE"


@dataclass(frozen=True)
class FreeSpaceEvidence:
    state_timestamp: int
    states: tuple[str, ...]
    occupied_entity_ids: tuple[WorldEntityId, ...]
    unknown_fraction: float
    validation_status: str = "UNVERIFIED"
    unseen_and_occluded: str = "UNKNOWN"


@dataclass(frozen=True)
class CorridorAnalysis:
    session_id: str
    state_timestamp: int
    corridor: UserCorridorState
    entity_relations: tuple[EntityCorridorRelation, ...]
    surface_evidence: CorridorSurfaceEvidence
    free_space_evidence: FreeSpaceEvidence
    quality: str
    provenance: ComponentProvenance
    world_provenance: ComponentProvenance
    calibration_id: str | None
    world_schema_version: int
    schema_version: int = 1


class CorridorAnalyzer(Protocol):
    def analyze(self, state: WorldState) -> CorridorAnalysis: ...
