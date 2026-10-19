"""Camera compensation and robust image-motion summaries; no physical object speed."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from .contracts import ComponentProvenance
from .flow import FramePair, SparseFlowObservation, frozen_float, frozen_mask
from .tracking_types import TrackId, TrackSet


class ScaleStatus(StrEnum):
    NONE = "NONE"
    UP_TO_SCALE = "UP_TO_SCALE"
    DEPTH_SCALED_RESEARCH = "DEPTH_SCALED_RESEARCH"


@dataclass(frozen=True)
class MotionQuality:
    state: str
    reason: str
    features: int
    inliers: int
    coverage: float
    inlier_ratio: float
    residual_pixels: float | None = None
    homography_support: float | None = None
    calibration_quality: str = "UNKNOWN"


@dataclass(frozen=True, eq=False)
class CameraMotionEstimate:
    """Static point convention: X_camera_B = R @ X_camera_A + t, not camera travel."""

    pair: FramePair
    rotation: NDArray[np.float64] | None
    translation_direction: NDArray[np.float64] | None
    scale_status: ScaleStatus
    quality: MotionQuality
    provenance: ComponentProvenance
    started_ns: int
    completed_ns: int
    research_translation: NDArray[np.float64] | None = None
    scale_source: ComponentProvenance | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.started_ns <= self.completed_ns:
            raise ValueError("Invalid processing timing")
        r = self.rotation
        if r is not None:
            if (
                r.shape != (3, 3)
                or not np.isfinite(r).all()
                or not np.allclose(r.T @ r, np.eye(3), atol=1e-6)
                or not np.isclose(np.linalg.det(r), 1, atol=1e-6)
            ):
                raise ValueError("Proper finite rotation required")
            object.__setattr__(self, "rotation", frozen_float(r))
        t = self.translation_direction
        if t is not None:
            if (
                r is None
                or t.shape != (3,)
                or not np.isfinite(t).all()
                or not np.isclose(np.linalg.norm(t), 1)
            ):
                raise ValueError("Unit translation direction required")
            object.__setattr__(self, "translation_direction", frozen_float(t))
        if not isinstance(self.scale_status, ScaleStatus):
            raise ValueError("Explicit scale status required")
        if self.scale_status == ScaleStatus.NONE and (
            t is not None or self.research_translation is not None
        ):
            raise ValueError("Unscaled state cannot contain translation")
        if self.scale_status == ScaleStatus.UP_TO_SCALE and (
            t is None or self.research_translation is not None
        ):
            raise ValueError("Direction only, not metric translation")
        if self.scale_status == ScaleStatus.DEPTH_SCALED_RESEARCH:
            v = self.research_translation
            if (
                r is None
                or v is None
                or v.shape != (3,)
                or not np.isfinite(v).all()
                or self.scale_source is None
            ):
                raise ValueError("Research scale requires depth provenance")
            object.__setattr__(self, "research_translation", frozen_float(v))


class EgoMotionEstimator(Protocol):
    def estimate(
        self, flow: SparseFlowObservation, excluded: NDArray[np.bool_] | None = None
    ) -> CameraMotionEstimate: ...


@dataclass(frozen=True, eq=False)
class ResidualFlow:
    pair: FramePair
    points_b: NDArray[np.float64]
    displacement: NDArray[np.float64]
    expected_displacement: NDArray[np.float64]
    valid: NDArray[np.bool_]
    compensation: str
    flow_provenance: ComponentProvenance
    motion_provenance: ComponentProvenance

    def __post_init__(self) -> None:
        n = len(self.valid)
        if self.valid.dtype != np.bool_ or self.valid.shape != (n,) or n > 4096:
            raise ValueError("Invalid residual mask")
        for name in ("points_b", "displacement", "expected_displacement"):
            v = getattr(self, name)
            if v.shape != (n, 2) or not np.isfinite(v).all():
                raise ValueError("Invalid residual vectors")
            object.__setattr__(self, name, frozen_float(v))
        object.__setattr__(self, "valid", frozen_mask(self.valid))


@dataclass(frozen=True)
class TrackImageMotionObservation:
    track_id: TrackId
    pair: FramePair
    median_displacement_pixels: tuple[float, float]
    median_rate_pixels_per_second: tuple[float, float]
    mad_pixels: tuple[float, float]
    samples: int
    valid_fraction: float
    compensation: str
    quality: str = "UNCALIBRATED_IMAGE_RESIDUAL"


def sample_tracks(
    tracks: TrackSet, residual: ResidualFlow, inset: float = 0.15, minimum: int = 3
) -> tuple[TrackImageMotionObservation, ...]:
    if tracks.identity != residual.pair.b or tracks.session_id != residual.pair.session_id:
        raise ValueError("Track/residual identity mismatch")
    if not 0 <= inset < 0.5 or minimum < 1:
        raise ValueError("Invalid sampling policy")
    out = []
    for track in tracks.tracks:
        if track.track_id.session_id != tracks.session_id:
            raise ValueError("Track belongs to another session")
        if (
            track.observation_status != "OBSERVED"
            or track.latest_observed_ns != tracks.identity.observation_ns
        ):
            continue
        box = track.latest_observed_bbox
        dx, dy = (box.x2 - box.x1) * inset, (box.y2 - box.y1) * inset
        x, y = residual.points_b.T
        region = (x >= box.x1 + dx) & (x < box.x2 - dx) & (y >= box.y1 + dy) & (y < box.y2 - dy)
        valid = region & residual.valid
        if int(valid.sum()) < minimum:
            continue
        values = residual.displacement[valid]
        median = np.median(values, axis=0)
        mad = np.median(np.abs(values - median), axis=0)
        rate = median / residual.pair.dt_seconds
        out.append(
            TrackImageMotionObservation(
                track.track_id,
                residual.pair,
                (float(median[0]), float(median[1])),
                (float(rate[0]), float(rate[1])),
                (float(mad[0]), float(mad[1])),
                int(valid.sum()),
                float(valid.sum() / region.sum()),
                residual.compensation,
            )
        )
    return tuple(out)
