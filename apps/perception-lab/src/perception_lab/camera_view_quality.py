"""Bounded image diagnostics, not a visibility or safety certification."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Literal, Self

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .config import canonical_hash
from .contracts import Frame, FrameIdentity, PixelFormat


class ViewStatus(StrEnum):
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    UNUSABLE = "UNUSABLE"
    UNKNOWN = "UNKNOWN"


class ViewQualityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)
    version: Literal["deterministic-view-v1"] = "deterministic-view-v1"
    sample_side: Annotated[int, Field(ge=16, le=256)] = 128
    minimum_side: Annotated[int, Field(ge=8, le=256)] = 16
    dark_pixel: Annotated[float, Field(ge=0, le=255)] = 12.0
    bright_pixel: Annotated[float, Field(ge=0, le=255)] = 245.0
    unusable_fraction: Annotated[float, Field(gt=0.5, le=1)] = 0.98
    degraded_fraction: Annotated[float, Field(gt=0, le=1)] = 0.80
    uniform_std: Annotated[float, Field(ge=0, le=255)] = 2.0
    minimum_entropy_bits: Annotated[float, Field(ge=0, le=8)] = 1.0
    blur_laplacian_variance: Annotated[float, Field(ge=0, le=100000)] = 8.0
    smear_anisotropy: Annotated[float, Field(ge=1, le=1000)] = 20.0
    smear_min_gradient: Annotated[float, Field(gt=0, le=255)] = 2.0

    @model_validator(mode="after")
    def thresholds(self) -> Self:
        if self.dark_pixel >= self.bright_pixel:
            raise ValueError("Exposure thresholds must be ordered")
        if self.degraded_fraction >= self.unusable_fraction:
            raise ValueError("Exposure severity thresholds must be ordered")
        if self.minimum_side > self.sample_side:
            raise ValueError("Minimum image size exceeds sample bound")
        return self


@dataclass(frozen=True)
class ViewDiagnostics:
    sampled_pixels: int
    mean_luminance: float
    luminance_std: float
    dark_fraction: float
    bright_fraction: float
    entropy_bits: float
    laplacian_variance: float
    gradient_anisotropy: float


@dataclass(frozen=True)
class CameraViewQuality:
    identity: FrameIdentity
    status: ViewStatus
    reasons: tuple[str, ...]
    indicators: tuple[str, ...]
    diagnostics: ViewDiagnostics | None
    configuration_hash: str
    detector_version: str

    @property
    def permits_scene_reasoning(self) -> bool:
        # UNKNOWN is not positive evidence that a camera can see the scene.
        return self.status in (ViewStatus.GOOD, ViewStatus.DEGRADED)


class CameraViewQualityEstimator:
    def __init__(self, config: ViewQualityConfig) -> None:
        self.config = config
        self.configuration_hash = canonical_hash(config.model_dump())

    def estimate(self, frame: Frame) -> CameraViewQuality:
        c = self.config
        if (
            min(frame.height, frame.width) < c.minimum_side
            or frame.pixel_format == PixelFormat.RGBA
        ):
            # An alpha compositing policy is required before interpreting RGBA exposure.
            return CameraViewQuality(
                frame.identity,
                ViewStatus.UNKNOWN,
                ("INSUFFICIENT_SCENE",),
                (),
                None,
                self.configuration_hash,
                c.version,
            )
        ys = np.linspace(0, frame.height - 1, min(frame.height, c.sample_side), dtype=np.intp)
        xs = np.linspace(0, frame.width - 1, min(frame.width, c.sample_side), dtype=np.intp)
        sample = frame.pixels[np.ix_(ys, xs)].astype(np.float32)
        if frame.pixel_format == PixelFormat.GRAY:
            gray = sample[:, :, 0]
        else:
            weights = (0.299, 0.587, 0.114)
            if frame.pixel_format == PixelFormat.BGR:
                weights = weights[::-1]
            gray = np.sum(sample * np.asarray(weights, dtype=np.float32), axis=2)
        counts = np.bincount(np.clip(gray, 0, 255).astype(np.uint8).ravel(), minlength=256)
        probabilities = counts[counts > 0] / gray.size
        entropy = float(-np.sum(probabilities * np.log2(probabilities)))
        laplacian = (
            gray[:-2, 1:-1]
            + gray[2:, 1:-1]
            + gray[1:-1, :-2]
            + gray[1:-1, 2:]
            - 4 * gray[1:-1, 1:-1]
        )
        gx = float(np.mean(np.abs(np.diff(gray, axis=1))))
        gy = float(np.mean(np.abs(np.diff(gray, axis=0))))
        anisotropy = (max(gx, gy) + 1e-6) / (min(gx, gy) + 1e-6)
        metrics = ViewDiagnostics(
            int(gray.size),
            float(np.mean(gray)),
            float(np.std(gray)),
            float(np.mean(gray <= c.dark_pixel)),
            float(np.mean(gray >= c.bright_pixel)),
            entropy,
            float(np.var(laplacian)),
            anisotropy,
        )
        reasons: list[str] = []
        indicators: list[str] = []
        unusable = False
        for fraction, reason in (
            (metrics.dark_fraction, "TOO_DARK"),
            (metrics.bright_fraction, "OVEREXPOSED"),
        ):
            if fraction >= c.degraded_fraction:
                reasons.append(reason)
            unusable |= fraction >= c.unusable_fraction
        if metrics.luminance_std <= c.uniform_std or entropy < c.minimum_entropy_bits:
            reasons.append("INSUFFICIENT_SCENE")
            indicators.append("OCCLUSION_LIKE_UNIFORMITY")
        if metrics.laplacian_variance < c.blur_laplacian_variance:
            indicators.append("LOW_SPATIAL_DETAIL")
            if "INSUFFICIENT_SCENE" not in reasons:
                reasons.append("INSUFFICIENT_SCENE")
        if anisotropy >= c.smear_anisotropy and max(gx, gy) >= c.smear_min_gradient:
            indicators.append("DIRECTIONAL_TEXTURE_OR_MOTION_SMEAR")
        # Texture cannot distinguish a plain wall from a covered lens, or stripes from smear.
        status = (
            ViewStatus.UNUSABLE
            if unusable
            else (ViewStatus.DEGRADED if reasons else ViewStatus.GOOD)
        )
        return CameraViewQuality(
            frame.identity,
            status,
            tuple(reasons),
            tuple(indicators),
            metrics,
            self.configuration_hash,
            c.version,
        )
