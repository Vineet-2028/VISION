"""Immutable image-space temporal identity; never person identity or world velocity."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .contracts import ComponentProvenance, FrameIdentity
from .detection import Box, DetectionBatch, ObjectClass


class DetectorEvidence(StrEnum):
    NO_DETECTOR_RUN = "NO_DETECTOR_RUN"
    SUCCESS = "SUCCESS"
    SUCCESS_EMPTY = "SUCCESS_EMPTY"
    FAILURE = "FAILURE"
    UNAVAILABLE = "UNAVAILABLE"


class Lifecycle(StrEnum):
    TENTATIVE = "TENTATIVE"
    CONFIRMED = "CONFIRMED"
    LOST = "LOST"
    REMOVED = "REMOVED"


@dataclass(frozen=True, order=True)
class TrackId:
    session_id: str
    serial: int

    def __post_init__(self) -> None:
        if not self.session_id or self.serial < 1:
            raise ValueError("Invalid track identity")


@dataclass(frozen=True)
class TrackObservation:
    identity: FrameIdentity
    box: Box
    category: ObjectClass
    confidence: float
    association_quality: float
    detector: ComponentProvenance
    status: str = "OBSERVED"


@dataclass(frozen=True)
class TrackSnapshot:
    track_id: TrackId
    lifecycle: Lifecycle
    observation_status: str
    category: ObjectClass
    category_confidence: float
    bbox: Box
    predicted_bbox: Box
    latest_observed_bbox: Box
    latest_observed_ns: int
    state_ns: int
    age_ns: int
    observation_age_ns: int
    hits: int
    misses: int
    consecutive_hits: int
    consecutive_misses: int
    observation_confidence: float
    quality: float
    image_velocity_pixels_per_second: tuple[float, ...]
    uncertainty_proxy: float
    history: tuple[TrackObservation, ...]
    detector_provenance: ComponentProvenance
    latest_failure: str | None
    # Geometry remains explicitly unavailable without validated camera calibration.
    bearing_radians: tuple[float, float] | None = None


@dataclass(frozen=True)
class TrackSet:
    session_id: str
    identity: FrameIdentity
    tracks: tuple[TrackSnapshot, ...]
    removed: tuple[TrackId, ...]
    detector_evidence: DetectorEvidence
    diagnostics: tuple[str, ...]
    provenance: ComponentProvenance
    schema_version: int = 1


class MultiObjectTracker(Protocol):
    provenance: ComponentProvenance

    def update(
        self,
        session_id: str,
        identity: FrameIdentity,
        evidence: DetectorEvidence,
        batch: DetectionBatch | None = None,
        failure_code: str | None = None,
    ) -> TrackSet: ...

    def reset(self, session_id: str, source_id: str, width: int, height: int) -> None: ...

    def close(self) -> None: ...
