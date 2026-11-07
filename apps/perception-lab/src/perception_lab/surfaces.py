"""Conservative image-space evidence; no navigation, accessibility or safety state."""

from dataclasses import asdict, dataclass
from enum import IntFlag
from math import ceil, floor

import cv2
import numpy as np
from numpy.typing import NDArray

from .contracts import ComponentProvenance, FrameIdentity
from .depth import DepthFrame
from .detection import Box, DetectionBatch, ObjectClass
from .semantics import (
    ObservationStatus,
    SemanticFrame,
    SemanticQuality,
    own_labels,
    restore_labels,
)
from .semantics import (
    SemanticClass as C,
)
from .tracking_types import TrackSet


class SurfaceFlag(IntFlag):
    UNKNOWN = 1
    GROUND_CANDIDATE = 2
    POTENTIAL_TRAVERSABLE = 4
    OBSTACLE_EVIDENCE = 8
    OCCUPIED_REGION = 16
    BOUNDARY = 32


@dataclass(frozen=True)
class SurfacePolicy:
    minimum_region_pixels: int = 1
    maximum_regions: int = 128
    maximum_overlay_fraction: float = 0.25

    def __post_init__(self) -> None:
        if (
            not 1 <= self.minimum_region_pixels <= 4096
            or not 1 <= self.maximum_regions <= 256
            or not 0 < self.maximum_overlay_fraction <= 0.5
        ):
            raise ValueError("Invalid bounded surface policy")


@dataclass(frozen=True)
class SurfaceRegion:
    region_id: int
    label: C
    pixel_area: int
    box: Box
    connected_to_bottom: bool
    # Exact boundary remains in the compact mask. Box edges use continuous camera coordinates.


@dataclass(frozen=True, eq=False)
class SurfaceEvidenceFrame:
    session_id: str
    identity: FrameIdentity
    observed_identity: FrameIdentity
    status: ObservationStatus
    evidence: NDArray[np.uint8]
    regions: tuple[SurfaceRegion, ...]
    quality: SemanticQuality
    semantic_provenance: ComponentProvenance
    camera_image_id: str
    detection_provenance: ComponentProvenance | None = None
    track_provenance: ComponentProvenance | None = None
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            self.evidence.dtype != np.uint8
            or self.evidence.ndim != 2
            or not 0 < self.evidence.size <= 8_294_400
            or len(self.regions) > 256
            or not isinstance(self.regions, tuple)
            or not self.session_id
            or not self.camera_image_id
            or self.identity.source_id != self.observed_identity.source_id
            or self.identity.timing != self.observed_identity.timing
            or self.identity.observation_ns < self.observed_identity.observation_ns
            or self.identity.sequence < self.observed_identity.sequence
            or not isinstance(self.status, ObservationStatus)
            or not isinstance(self.quality, SemanticQuality)
            or np.any(self.evidence > 63)
        ):
            raise ValueError("Invalid bounded surface evidence")
        unknown = self.evidence & int(SurfaceFlag.UNKNOWN) != 0
        traversable = self.evidence & int(SurfaceFlag.POTENTIAL_TRAVERSABLE) != 0
        if np.any(unknown & traversable):
            raise ValueError("Unknown cannot be potential traversable evidence")
        object.__setattr__(self, "evidence", own_labels(self.evidence))

    def summary(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "identity": asdict(self.identity),
            "observed_identity": asdict(self.observed_identity),
            "status": self.status,
            "quality": self.quality,
            "camera_image_id": self.camera_image_id,
            "dimensions": [self.evidence.shape[1], self.evidence.shape[0]],
            "flag_pixels": {
                f.name: int(np.count_nonzero(self.evidence & int(f))) for f in SurfaceFlag
            },
            "regions": [asdict(r) for r in self.regions],
            "semantic_provenance": asdict(self.semantic_provenance),
            "detection_provenance": asdict(self.detection_provenance)
            if self.detection_provenance
            else None,
            "track_provenance": asdict(self.track_provenance) if self.track_provenance else None,
            "diagnostics": self.diagnostics,
        }


def boundaries(labels: NDArray[np.uint8]) -> NDArray[np.bool_]:
    result = np.zeros(labels.shape, dtype=np.bool_)
    result[1:] |= labels[1:] != labels[:-1]
    result[:-1] |= labels[1:] != labels[:-1]
    result[:, 1:] |= labels[:, 1:] != labels[:, :-1]
    result[:, :-1] |= labels[:, 1:] != labels[:, :-1]
    return result


class SurfaceEvidenceExtractor:
    def __init__(self, policy: SurfacePolicy | None = None) -> None:
        self.policy = policy or SurfacePolicy()

    def extract(
        self,
        semantic: SemanticFrame,
        detections: DetectionBatch | None = None,
        tracks: TrackSet | None = None,
    ) -> SurfaceEvidenceFrame:
        if detections is not None and detections.identity != semantic.identity:
            raise ValueError("Detection/semantic frame mismatch")
        if tracks is not None and (
            tracks.identity != semantic.identity or tracks.session_id != semantic.session_id
        ):
            raise ValueError("Track/semantic session or frame mismatch")
        labels = restore_labels(semantic)
        evidence = np.zeros(labels.shape, dtype=np.uint8)
        unavailable = semantic.status in {ObservationStatus.STALE, ObservationStatus.UNAVAILABLE}
        ground = np.isin(labels, [C.SIDEWALK, C.ROAD, C.FLOOR, C.PATH, C.GROUND_OTHER, C.GRASS])
        potential = np.isin(labels, [C.SIDEWALK, C.FLOOR, C.PATH])
        unknown = np.isin(labels, [C.UNKNOWN, C.BACKGROUND_OTHER, C.GROUND_OTHER, C.GRASS])
        obstacle = np.isin(
            labels,
            [
                C.WALL,
                C.BUILDING,
                C.PERSON,
                C.BICYCLE,
                C.MOTORCYCLE,
                C.VEHICLE,
                C.POLE,
                C.FENCE,
                C.OBJECT_OTHER,
                C.VEGETATION,
                C.STAIRS,
                C.CURB,
            ],
        )
        evidence[ground] |= int(SurfaceFlag.GROUND_CANDIDATE)
        evidence[potential] |= int(SurfaceFlag.POTENTIAL_TRAVERSABLE)
        evidence[unknown] |= int(SurfaceFlag.UNKNOWN)
        evidence[obstacle] |= int(SurfaceFlag.OBSTACLE_EVIDENCE)
        evidence[boundaries(labels)] |= int(SurfaceFlag.BOUNDARY)
        diagnostics: list[str] = []
        regions: list[SurfaceRegion] = []
        # Process one class at a time: never retain a full map for each class.
        for label in (C.SIDEWALK, C.ROAD, C.FLOOR, C.PATH, C.STAIRS, C.CURB, C.GROUND_OTHER):
            count, components, stats, _ = cv2.connectedComponentsWithStats(
                (labels == label).astype(np.uint8), connectivity=8
            )
            bottom_ids = set(int(v) for v in np.unique(components[-1]))
            # Largest components first; stable ties. Contour complexity is bounded by masks.
            order = np.argsort(-stats[1:, cv2.CC_STAT_AREA], kind="stable") + 1
            for index in order[: self.policy.maximum_regions]:
                x, y, w, h, area = (int(v) for v in stats[index])
                if area < self.policy.minimum_region_pixels:
                    continue  # Metadata filtering only; original masks never filled/erased.
                if len(regions) == self.policy.maximum_regions:
                    diagnostics.append("REGION_METADATA_TRUNCATED")
                    break
                regions.append(
                    SurfaceRegion(
                        len(regions) + 1,
                        label,
                        area,
                        Box(x, y, x + w, y + h),
                        int(index) in bottom_ids,
                    )
                )
            if count - 1 > self.policy.maximum_regions:
                diagnostics.append("REGION_METADATA_TRUNCATED")
        boxes: list[Box] = []
        if detections is not None:
            boxes.extend(
                d.box
                for d in detections.detections
                if d.entity_observation is not None or d.label != ObjectClass.UNKNOWN
            )
        if tracks is not None:
            boxes.extend(
                t.latest_observed_bbox
                for t in tracks.tracks
                if t.observation_status == "OBSERVED"
                and t.latest_observed_ns == semantic.identity.observation_ns
                and (t.entity_observation is not None or t.category != ObjectClass.UNKNOWN)
            )
        height, width = labels.shape
        for box in boxes[:512]:
            x1, y1 = max(0, floor(box.x1)), max(0, floor(box.y1))
            x2, y2 = min(width, ceil(box.x2)), min(height, ceil(box.y2))
            if x2 <= x1 or y2 <= y1:
                continue
            if (x2 - x1) * (y2 - y1) > labels.size * self.policy.maximum_overlay_fraction:
                diagnostics.append("OVERSIZED_OVERLAY_IGNORED")
                continue
            # Separate occupancy evidence: never erase or relabel the semantic mask.
            evidence[y1:y2, x1:x2] |= int(SurfaceFlag.OCCUPIED_REGION)
        if len(boxes) > 512:
            diagnostics.append("OVERLAY_LIMIT")
        if unavailable:
            evidence.fill(int(SurfaceFlag.UNKNOWN))
            regions.clear()
        return SurfaceEvidenceFrame(
            semantic.session_id,
            semantic.identity,
            semantic.observed_identity,
            semantic.status,
            evidence,
            tuple(regions),
            SemanticQuality.UNAVAILABLE if unavailable else SemanticQuality.DEGRADED,
            semantic.provenance,
            semantic.mapping.camera_image_id,
            detections.provenance if detections else None,
            tracks.provenance if tracks else None,
            tuple(sorted(set(diagnostics))),
        )


def depth_consistency(semantic: SemanticFrame, depth: DepthFrame) -> dict[str, object]:
    """Dimensionless neighbor discontinuity diagnostic, not height/slope/drop detection."""
    if (
        semantic.identity != depth.identity
        or semantic.mapping.camera_image_id != depth.mapping.camera_image_id
        or semantic.mapping.camera_dimensions != depth.mapping.camera_dimensions
    ):
        raise ValueError("Depth/semantic identity mismatch")
    # Exact native-grid join only. Resampling depth requires a separate explicit policy.
    if semantic.mapping.fingerprint != depth.mapping.fingerprint:
        return {"status": "UNAVAILABLE_GRID_MISMATCH", "depth_provenance": asdict(depth.provenance)}
    ground = np.isin(semantic.labels, [C.SIDEWALK, C.ROAD, C.PATH, C.FLOOR])
    valid = ground[:, 1:] & ground[:, :-1] & depth.valid[:, 1:] & depth.valid[:, :-1]
    values = depth.values
    scale = max(float(np.median(np.abs(values[depth.valid]))) if depth.valid.any() else 0, 1e-6)
    jumps = np.abs(values[:, 1:] - values[:, :-1]) / scale
    return {
        "status": "QUALITATIVE_ONLY",
        "depth_provenance": asdict(depth.provenance),
        "neighbor_pairs": int(valid.sum()),
        "relative_jump_p95": float(np.percentile(jumps[valid], 95)) if valid.any() else None,
    }
