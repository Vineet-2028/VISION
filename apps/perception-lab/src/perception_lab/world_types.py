"""Compact immutable world-state schema v1. No inference or decision policy."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .contracts import ComponentProvenance, FrameIdentity, FrameResult
from .depth_sampling import DepthEstimate
from .depth_spatial import CameraPointEstimate, SuppliedDepthPose, WorldPointEstimate
from .detection import Box, ObjectClass
from .motion import ScaleStatus, TrackImageMotionObservation
from .perceived_entity import PerceivedEntityObservation
from .surfaces import SurfaceRegion
from .track_semantics import TrackSemanticState
from .tracking_types import TrackId
from .user_heading import UserMotionHeadingEstimate


class EvidenceStatus(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    PREDICTED = "PREDICTED"
    PROPAGATED = "PROPAGATED"
    DEGRADED = "DEGRADED"
    UNRELIABLE = "UNRELIABLE"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"


class EntityLifecycle(StrEnum):
    TENTATIVE = "TENTATIVE"
    ACTIVE = "ACTIVE"
    PREDICTED = "PREDICTED"
    LOST = "LOST"


@dataclass(frozen=True, order=True)
class WorldEntityId:
    session_id: str
    serial: int


@dataclass(frozen=True)
class EvidenceSource:
    subsystem: str
    identity: FrameIdentity | None
    age_ns: int | None
    status: EvidenceStatus
    observation_status: str
    quality: str
    validation_status: str
    provenance: tuple[ComponentProvenance, ...] = ()
    reason: str | None = None


@dataclass(frozen=True)
class EntityHistory:
    identity: FrameIdentity
    box: Box
    category: ObjectClass
    observation_status: str
    quality: float
    depth_value: float | None = None
    depth_kind: str | None = None
    camera_point_meters: tuple[float, float, float] | None = None
    bearing_radians: tuple[float, float] | None = None
    world_point: WorldPointEstimate | None = None
    position_sources: tuple[EvidenceSource, ...] = ()
    calibration_id: str | None = None


@dataclass(frozen=True)
class WorldEntity:
    entity_id: WorldEntityId
    source_track_id: TrackId
    category: ObjectClass
    category_confidence: float
    lifecycle: EntityLifecycle
    observation_status: str
    latest_observed_ns: int
    state_timestamp: int
    observation_age_ns: int
    image_geometry: Box
    bearing_radians: tuple[float, float] | None
    track_evidence: EvidenceSource
    depth: DepthEstimate | None
    depth_evidence: EvidenceSource
    position_camera: CameraPointEstimate | None
    position_world: WorldPointEstimate | None
    position_status: str
    position_sources: tuple[EvidenceSource, ...]
    image_motion: TrackImageMotionObservation | None
    motion_evidence: EvidenceSource
    history: tuple[EntityHistory, ...]
    quality: str
    reasons: tuple[str, ...]
    semantic_evidence: EvidenceSource | None = None
    semantic_center_label: str | None = None
    # Optional semantic/region evidence. Its original timestamp is never refreshed by prediction.
    entity_observation: PerceivedEntityObservation | None = None
    track_semantics: TrackSemanticState | None = None


@dataclass(frozen=True)
class WorldCameraState:
    pose: SuppliedDepthPose | None
    pose_evidence: EvidenceSource
    calibration_id: str | None
    calibration_quality: str
    motion_evidence: EvidenceSource
    motion_pair: tuple[FrameIdentity, FrameIdentity] | None
    rotation: tuple[float, ...] | None
    translation_direction: tuple[float, ...] | None
    scale_status: ScaleStatus
    imu_status: str = "UNAVAILABLE"
    localization: str = "SESSION_LOCAL; DRIFT_UNVALIDATED"


@dataclass(frozen=True)
class WorldSurfaceState:
    evidence: EvidenceSource
    validation_status: str
    camera_image_id: str | None
    dimensions: tuple[int, int] | None
    regions: tuple[SurfaceRegion, ...]
    flag_pixels: tuple[tuple[str, int], ...]
    semantic_class_pixels: tuple[tuple[str, int], ...]
    geometry_status: str = "IMAGE_SPACE_ONLY; GROUND_PLANE_UNAVAILABLE"
    projected_ground: tuple["SurfaceGroundCandidate", ...] = ()
    # Bounded regular image samples (x, y, SurfaceFlag bits), not an occupancy map.
    samples: tuple[tuple[float, float, int], ...] = ()


@dataclass(frozen=True)
class SurfaceGroundCandidate:
    region_id: int
    source_pixel: tuple[float, float]
    position_meters: tuple[float, float, float]
    identity: FrameIdentity
    world_frame_id: str
    provenance: tuple[ComponentProvenance, ...]
    source: str = "GROUND_PLANE_PROJECTED"
    validation_status: str = "UNVERIFIED"
    uncertainty_status: str = "UNKNOWN"


@dataclass(frozen=True)
class Capability:
    name: str
    status: EvidenceStatus
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class WorldSceneQuality:
    state: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class WorldState:
    session_id: str
    state_timestamp: int
    camera_state: WorldCameraState
    entities: tuple[WorldEntity, ...]
    surface_state: WorldSurfaceState
    scene_quality: WorldSceneQuality
    source_ages: tuple[tuple[str, int | None], ...]
    subsystem_status: tuple[EvidenceSource, ...]
    capabilities: tuple[Capability, ...]
    provenance: ComponentProvenance
    diagnostics: tuple[str, ...]
    schema_version: int = 1
    image_geometry: "WorldImageGeometry | None" = None
    ground_plane: "SuppliedGroundPlane | None" = None
    user_motion_heading: UserMotionHeadingEstimate | None = None


@dataclass(frozen=True)
class WorldImageGeometry:
    camera_image_id: str
    width: int
    height: int
    evidence: EvidenceSource


@dataclass(frozen=True)
class SuppliedGroundPlane:
    """Explicit local assumption supplied by an adapter, never inferred from labels.

    normal points toward the camera/up. Frame is CAMERA or LOCAL_WORLD; pose is
    required for the latter. Plane evidence binds clock/time and provenance.
    """

    coordinate_frame: str
    frame_id: str
    point_meters: tuple[float, float, float]
    normal: tuple[float, float, float]
    evidence: EvidenceSource


class WorldModel(Protocol):
    """Pipeline-facing replacement boundary; consumers depend only on WorldState."""

    def consume(self, result: FrameResult) -> WorldState: ...
    def snapshot(self, timestamp: int) -> WorldState: ...
    def reset(self, session_id: str, source_id: str) -> None: ...
    def close(self) -> None: ...

    def ingest_entity_semantics(
        self,
        entity_id: WorldEntityId,
        track_id: TrackId,
        observation: PerceivedEntityObservation,
        now: int,
    ) -> bool: ...
