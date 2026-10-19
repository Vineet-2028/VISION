"""Bounded robust region sampling in original-camera continuous edge coordinates."""

from dataclasses import dataclass
from math import floor, isfinite
from typing import Literal

import numpy as np

from .contracts import ComponentProvenance, FrameIdentity
from .depth import DepthDirection, DepthFrame, DepthKind, DepthRepresentation
from .detection import Box, DetectionBatch
from .tracking_types import TrackId, TrackSet


@dataclass(frozen=True)
class SamplingPolicy:
    strategy: Literal["central", "eroded", "lower_center", "near_surface", "bottom_patch"] = (
        "eroded"
    )
    inset: float = 0.15
    grid: int = 16
    interpolation: Literal["nearest", "bilinear"] = "nearest"
    minimum_valid_fraction: float = 0.5

    def __post_init__(self) -> None:
        if self.strategy not in {
            "central",
            "eroded",
            "lower_center",
            "near_surface",
            "bottom_patch",
        }:
            raise ValueError("Unknown region strategy")
        if self.interpolation not in {"nearest", "bilinear"}:
            raise ValueError("Unknown interpolation")
        if not 0 <= self.inset < 0.5 or not 1 <= self.grid <= 64:
            raise ValueError("Invalid bounded sampling policy")
        if not 0 <= self.minimum_valid_fraction <= 1:
            raise ValueError("Invalid minimum valid fraction")


DEFAULT_SAMPLING = SamplingPolicy()


@dataclass(frozen=True)
class RegionStatistics:
    p25: float
    median: float
    p75: float
    mad: float
    valid_fraction: float
    valid_samples: int
    attempted_samples: int


@dataclass(frozen=True)
class DepthEstimate:
    identity: FrameIdentity
    representation: DepthRepresentation
    value: float
    region: Box
    sample_pixel: tuple[float, float]
    statistics: RegionStatistics
    sampling_method: str
    provenance: ComponentProvenance
    camera_image_id: str
    camera_dimensions: tuple[int, int]
    transform_hash: str
    quality: str = "UNCALIBRATED_REGION_STATISTICS"
    uncertainty_status: str = "UNKNOWN"

    def __post_init__(self) -> None:
        if not isfinite(self.value) or not all(isfinite(v) for v in self.sample_pixel):
            raise ValueError("Finite depth estimate required")
        if self.representation.kind == DepthKind.METRIC and self.value <= 0:
            raise ValueError("Positive metric estimate required")
        if self.representation.minimum is not None and self.value < self.representation.minimum:
            raise ValueError("Depth below supported range")
        if self.representation.maximum is not None and self.value > self.representation.maximum:
            raise ValueError("Depth above supported range")

    @property
    def meters(self) -> float:
        if self.representation.kind != DepthKind.METRIC:
            raise ValueError("Relative depth has no meters")
        return self.value


def sample_pixel(depth: DepthFrame, u: float, v: float, method: str = "nearest") -> float | None:
    if method not in {"nearest", "bilinear"}:
        raise ValueError("Unknown interpolation")
    width, height = depth.mapping.camera_dimensions
    if not isfinite(u) or not isfinite(v) or not (0 <= u < width and 0 <= v < height):
        return None
    x, y = depth.mapping.forward(u, v)
    if not (0 <= x < depth.width and 0 <= y < depth.height):
        return None
    if method == "nearest":
        ix, iy = floor(x), floor(y)
        return float(depth.values[iy, ix]) if depth.valid[iy, ix] else None
    # Pixel centers are i+0.5. No border extrapolation and no invalid-neighbor fill.
    x, y = x - 0.5, y - 0.5
    x0, y0 = floor(x), floor(y)
    total = 0.0
    for ix, wx in ((x0, 1 - (x - x0)), (x0 + 1, x - x0)):
        for iy, wy in ((y0, 1 - (y - y0)), (y0 + 1, y - y0)):
            weight = wx * wy
            if weight == 0:
                continue
            if not (0 <= ix < depth.width and 0 <= iy < depth.height) or not depth.valid[iy, ix]:
                return None
            total += weight * float(depth.values[iy, ix])
    return total


def sample_region(
    depth: DepthFrame, box: Box, policy: SamplingPolicy = DEFAULT_SAMPLING
) -> DepthEstimate | None:
    width, height = depth.mapping.camera_dimensions
    # Off-image regions are not silently clipped into a different observation.
    if box.area <= 0 or box.x1 < 0 or box.y1 < 0 or box.x2 > width or box.y2 > height:
        return None
    dx, dy = box.x2 - box.x1, box.y2 - box.y1
    inset = 0.25 if policy.strategy == "central" else policy.inset
    left, right = box.x1 + dx * inset, box.x2 - dx * inset
    top, bottom = box.y1 + dy * inset, box.y2 - dy * inset
    if policy.strategy == "lower_center":
        top = box.y1 + dy * 0.5
    elif policy.strategy == "bottom_patch":
        left, right = box.x1 + dx * 0.4, box.x1 + dx * 0.6
        top, bottom = box.y1 + dy * 0.8, box.y2
    region = Box(left, top, right, bottom)
    values = []
    if policy.interpolation == "nearest":
        positions = (np.arange(policy.grid, dtype=np.float64) + 0.5) / policy.grid
        us, vs = np.meshgrid(left + positions * (right - left), top + positions * (bottom - top))
        xs, ys = depth.mapping.forward_many(us.ravel(), vs.ravel())
        inside = (xs >= 0) & (xs < depth.width) & (ys >= 0) & (ys < depth.height)
        ix, iy = np.floor(xs[inside]).astype(np.int64), np.floor(ys[inside]).astype(np.int64)
        values = depth.values[iy, ix][depth.valid[iy, ix]].tolist()
    else:
        for row in range(policy.grid):
            for column in range(policy.grid):
                u = left + (column + 0.5) / policy.grid * (right - left)
                v = top + (row + 0.5) / policy.grid * (bottom - top)
                value = sample_pixel(depth, u, v, policy.interpolation)
                if value is not None:
                    values.append(value)
    fraction = len(values) / policy.grid**2
    if not values or fraction < policy.minimum_valid_fraction:
        return None
    q25, median, q75 = (float(v) for v in np.percentile(values, [25, 50, 75]))
    mad = float(np.median(np.abs(np.asarray(values) - median)))
    value = median
    if policy.strategy == "near_surface":
        value = q25 if depth.representation.direction == DepthDirection.LARGER_IS_FARTHER else q75
    return DepthEstimate(
        depth.identity,
        depth.representation,
        value,
        region,
        ((left + right) / 2, (top + bottom) / 2),
        RegionStatistics(q25, median, q75, mad, fraction, len(values), policy.grid**2),
        policy.strategy + ":" + policy.interpolation,
        depth.provenance,
        depth.mapping.camera_image_id,
        depth.mapping.camera_dimensions,
        depth.mapping.fingerprint,
    )


def detection_depth(
    batch: DetectionBatch, depth: DepthFrame, policy: SamplingPolicy = DEFAULT_SAMPLING
) -> tuple[DepthEstimate | None, ...]:
    if batch.identity != depth.identity:
        raise ValueError("Detection/depth frame identity mismatch")
    return tuple(sample_region(depth, d.box, policy) for d in batch.detections)


@dataclass(frozen=True)
class TrackDepthObservation:
    track_id: TrackId
    identity: FrameIdentity
    observation_status: str
    estimate: DepthEstimate | None
    depth_age_ns: int | None


def track_depth(
    tracks: TrackSet, depth: DepthFrame | None, policy: SamplingPolicy = DEFAULT_SAMPLING
) -> tuple[TrackDepthObservation, ...]:
    if depth is not None and depth.identity != tracks.identity:
        raise ValueError("Track/depth frame identity mismatch")
    observations = []
    for track in tracks.tracks:
        if track.track_id.session_id != tracks.session_id:
            raise ValueError("Track session mismatch")
        estimate = None
        if depth is not None and track.observation_status == "OBSERVED":
            if track.latest_observed_ns != tracks.identity.observation_ns:
                raise ValueError("Observed track timestamp mismatch")
            # Use the observed box, never the estimator's filtered/predicted box.
            estimate = sample_region(depth, track.latest_observed_bbox, policy)
        observations.append(
            TrackDepthObservation(
                track.track_id,
                tracks.identity,
                "EXACT_FRAME" if estimate is not None else "UNAVAILABLE",
                estimate,
                0 if estimate is not None else None,
            )
        )
    return tuple(observations)
