"""Versioned image evidence. Semantic classes never express safety decisions."""

from dataclasses import asdict, dataclass
from enum import IntEnum, StrEnum
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from .contracts import ComponentProvenance, FrameIdentity, TimingProvenance
from .geometry import ImageMapping
from .preprocessing import PreparedImage

TAXONOMY = "sentinel-surfaces-v1"
IGNORE = 255  # Annotation-only; never a predicted semantic class.
MAX_PIXELS = 8_294_400


class SemanticClass(IntEnum):
    UNKNOWN = 0
    SIDEWALK = 1
    ROAD = 2
    FLOOR = 3
    PATH = 4
    STAIRS = 5
    GRASS = 6
    VEGETATION = 7
    WALL = 8
    BUILDING = 9
    CURB = 10
    GROUND_OTHER = 11
    PERSON = 12
    BICYCLE = 13
    MOTORCYCLE = 14
    VEHICLE = 15
    POLE = 16
    FENCE = 17
    OBJECT_OTHER = 18
    BACKGROUND_OTHER = 19


class SemanticGroup(StrEnum):
    GROUND_SURFACE = "GROUND_SURFACE"
    STRUCTURE = "STRUCTURE"
    DYNAMIC_OBJECT = "DYNAMIC_OBJECT"
    STATIC_OBSTACLE = "STATIC_OBSTACLE"
    VEGETATION = "VEGETATION"
    UNKNOWN = "UNKNOWN"


def semantic_group(label: SemanticClass) -> SemanticGroup:
    if label in {
        SemanticClass.SIDEWALK,
        SemanticClass.ROAD,
        SemanticClass.FLOOR,
        SemanticClass.PATH,
        SemanticClass.GROUND_OTHER,
        SemanticClass.STAIRS,
        SemanticClass.CURB,
    }:
        return SemanticGroup.GROUND_SURFACE
    if label in {SemanticClass.GRASS, SemanticClass.VEGETATION}:
        return SemanticGroup.VEGETATION
    if label in {
        SemanticClass.PERSON,
        SemanticClass.BICYCLE,
        SemanticClass.MOTORCYCLE,
        SemanticClass.VEHICLE,
    }:
        return SemanticGroup.DYNAMIC_OBJECT
    if label in {SemanticClass.WALL, SemanticClass.BUILDING, SemanticClass.FENCE}:
        return SemanticGroup.STRUCTURE
    if label in {SemanticClass.POLE, SemanticClass.OBJECT_OTHER}:
        return SemanticGroup.STATIC_OBSTACLE
    return SemanticGroup.UNKNOWN


class ObservationStatus(StrEnum):
    OBSERVED = "OBSERVED"
    PROPAGATED = "PROPAGATED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


class SemanticQuality(StrEnum):
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    UNRELIABLE = "UNRELIABLE"
    UNAVAILABLE = "UNAVAILABLE"


def own_labels(labels: NDArray[np.uint8]) -> NDArray[np.uint8]:
    return np.frombuffer(labels.tobytes(), dtype=np.uint8).reshape(labels.shape)


@dataclass(frozen=True, eq=False)
class SemanticFrame:
    session_id: str
    identity: FrameIdentity
    observed_identity: FrameIdentity
    labels: NDArray[np.uint8]
    mapping: ImageMapping
    provenance: ComponentProvenance
    supported_classes: frozenset[SemanticClass]
    started_ns: int
    completed_ns: int
    status: ObservationStatus = ObservationStatus.OBSERVED
    quality: SemanticQuality = SemanticQuality.DEGRADED
    taxonomy: str = TAXONOMY
    mapping_version: str = "sentinel-v1"
    warp_count: int = 0

    def __post_init__(self) -> None:
        if (
            not self.session_id
            or self.taxonomy != TAXONOMY
            or not self.mapping_version
            or self.labels.dtype != np.uint8
            or self.labels.ndim != 2
            or not 0 < self.labels.size <= MAX_PIXELS
            or min(self.labels.shape) < 1
            or self.mapping.target_dimensions != (self.labels.shape[1], self.labels.shape[0])
            or self.identity.timing == TimingProvenance.UNKNOWN
            or self.identity.source_id != self.observed_identity.source_id
            or self.identity.timing != self.observed_identity.timing
            or self.identity.sequence < self.observed_identity.sequence
            or self.identity.observation_ns < self.observed_identity.observation_ns
            or self.started_ns < 0
            or self.completed_ns < self.started_ns
            or not isinstance(self.status, ObservationStatus)
            or not isinstance(self.quality, SemanticQuality)
            or not 0 <= self.warp_count <= 16
            or not isinstance(self.supported_classes, frozenset)
            or any(not isinstance(c, SemanticClass) for c in self.supported_classes)
        ):
            raise ValueError("Invalid semantic identity, dimensions, timing or taxonomy")
        actual = set(int(v) for v in np.unique(self.labels))
        if not actual <= {int(c) for c in self.supported_classes} | {0}:
            raise ValueError("Unsupported semantic label")
        if self.status == ObservationStatus.OBSERVED and (
            self.identity != self.observed_identity or self.warp_count != 0
        ):
            raise ValueError("Observed semantics must bind to the original observation")
        if self.status == ObservationStatus.PROPAGATED and (
            self.identity.sequence <= self.observed_identity.sequence
            or self.age_ns <= 0
            or self.warp_count == 0
        ):
            raise ValueError("Propagation requires explicit age and warp count")
        if self.status == ObservationStatus.UNAVAILABLE and np.any(self.labels):
            raise ValueError("Unavailable semantics cannot contain observed labels")
        object.__setattr__(self, "labels", own_labels(self.labels))

    @property
    def age_ns(self) -> int:
        return self.identity.observation_ns - self.observed_identity.observation_ns

    def summary(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "identity": asdict(self.identity),
            "observed_identity": asdict(self.observed_identity),
            "age_ns": self.age_ns,
            "status": self.status,
            "quality": self.quality,
            "taxonomy": self.taxonomy,
            "mapping_version": self.mapping_version,
            "transform_hash": self.mapping.fingerprint,
            "dimensions": self.mapping.target_dimensions,
            "camera_dimensions": self.mapping.camera_dimensions,
            "supported_classes": sorted(c.name for c in self.supported_classes),
            "class_pixels": {
                c.name: int(np.count_nonzero(self.labels == c)) for c in SemanticClass
            },
            "provenance": asdict(self.provenance),
            "warp_count": self.warp_count,
            "started_ns": self.started_ns,
            "completed_ns": self.completed_ns,
        }


class SemanticSegmenter(Protocol):
    provenance: ComponentProvenance

    def segment(self, image: PreparedImage, identity: FrameIdentity) -> SemanticFrame | None: ...


def restore_labels(frame: SemanticFrame) -> NDArray[np.uint8]:
    """Nearest native cell at original continuous-edge pixel centers; crop exterior unknown.

    Row chunks bound scratch arrays. No bilinear interpolation of integer class IDs.
    """
    width, height = frame.mapping.camera_dimensions
    if not 0 < width * height <= MAX_PIXELS:
        raise ValueError("Original image exceeds semantic pixel bound")
    result = np.zeros((height, width), dtype=np.uint8)
    x = np.arange(width, dtype=np.float64)[None, :] + 0.5
    for top in range(0, height, 128):
        y = np.arange(top, min(height, top + 128), dtype=np.float64)[:, None] + 0.5
        u, v = frame.mapping.forward_many(x, y)
        u, v = np.broadcast_arrays(u, v)
        valid = (u >= 0) & (v >= 0) & (u < frame.labels.shape[1]) & (v < frame.labels.shape[0])
        ix = np.clip(np.floor(u).astype(np.int64), 0, frame.labels.shape[1] - 1)
        iy = np.clip(np.floor(v).astype(np.int64), 0, frame.labels.shape[0] - 1)
        result[top : top + len(y)] = np.where(valid, frame.labels[iy, ix], 0)
    return result
