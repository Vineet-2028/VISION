"""Immutable pair observations. Pixel displacement is never physical velocity."""

from dataclasses import asdict, dataclass
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from .contracts import ComponentProvenance, FrameIdentity, TimingProvenance
from .geometry import ImageMapping


@dataclass(frozen=True)
class FramePair:
    session_id: str
    a: FrameIdentity
    b: FrameIdentity
    calibration_hash: str
    camera_image_id: str
    width: int
    height: int
    max_gap_ns: int = 1_000_000_000

    def __post_init__(self) -> None:
        if (
            not self.session_id
            or not self.calibration_hash
            or not self.camera_image_id
            or min(self.width, self.height) <= 0
            or not 0 < self.max_gap_ns <= 5_000_000_000
            or self.a.source_id != self.b.source_id
            or self.a.timing != self.b.timing
            or self.a.timing == TimingProvenance.UNKNOWN
            or self.b.sequence <= self.a.sequence
            or not 0 < self.b.observation_ns - self.a.observation_ns <= self.max_gap_ns
        ):
            raise ValueError("Incompatible or unsupported frame pair")

    @property
    def dt_seconds(self) -> float:
        return (self.b.observation_ns - self.a.observation_ns) / 1e9


def frozen_float(value: NDArray[np.float64]) -> NDArray[np.float64]:
    return np.frombuffer(np.asarray(value, dtype=np.float64).tobytes(), dtype=np.float64).reshape(
        value.shape
    )


def frozen_mask(value: NDArray[np.bool_]) -> NDArray[np.bool_]:
    return np.frombuffer(value.tobytes(), dtype=np.bool_).reshape(value.shape)


@dataclass(frozen=True, eq=False)
class SparseFlowObservation:
    pair: FramePair
    points_a: NDArray[np.float64]
    points_b: NDArray[np.float64]
    valid: NDArray[np.bool_]
    fb_error_pixels: NDArray[np.float64]
    provenance: ComponentProvenance
    started_ns: int
    completed_ns: int
    coordinate_space: str = "ORIGINAL_CAMERA_CONTINUOUS_EDGES"

    def __post_init__(self) -> None:
        n = len(self.points_a)
        if (
            self.points_a.shape != (n, 2)
            or self.points_b.shape != (n, 2)
            or self.valid.shape != (n,)
            or self.valid.dtype != np.bool_
            or self.fb_error_pixels.shape != (n,)
            or n > 4096
            or not np.isfinite(self.points_a).all()
            or not np.isfinite(self.points_b).all()
            or not np.isfinite(self.fb_error_pixels).all()
            or (self.fb_error_pixels < 0).any()
            or not 0 <= self.started_ns <= self.completed_ns
            or self.coordinate_space != "ORIGINAL_CAMERA_CONTINUOUS_EDGES"
        ):
            raise ValueError("Invalid sparse flow")
        bounds = np.array([self.pair.width, self.pair.height])
        inside = (
            (self.points_a >= 0)
            & (self.points_a < bounds)
            & (self.points_b >= 0)
            & (self.points_b < bounds)
        ).all(axis=1)
        object.__setattr__(self, "valid", frozen_mask(self.valid & inside))
        for name in ("points_a", "points_b", "fb_error_pixels"):
            object.__setattr__(self, name, frozen_float(getattr(self, name)))

    @property
    def identity(self) -> FrameIdentity:
        return self.pair.b

    @property
    def displacement(self) -> NDArray[np.float64]:
        return self.points_b - self.points_a

    def summary(self) -> dict[str, object]:
        return {
            "kind": "SPARSE",
            "pair": asdict(self.pair),
            "samples": len(self.valid),
            "valid_samples": int(self.valid.sum()),
            "quality": "UNCALIBRATED_FB_ERROR",
            "provenance": asdict(self.provenance),
            "started_ns": self.started_ns,
            "completed_ns": self.completed_ns,
            "coordinate_space": self.coordinate_space,
        }


@dataclass(frozen=True, eq=False)
class DenseFlowField:
    pair: FramePair
    vectors: NDArray[np.float64]
    valid: NDArray[np.bool_]
    fb_error_pixels: NDArray[np.float64]
    mapping: ImageMapping
    provenance: ComponentProvenance
    started_ns: int
    completed_ns: int

    def __post_init__(self) -> None:
        h, w = self.valid.shape
        if (
            self.vectors.shape != (h, w, 2)
            or self.valid.dtype != np.bool_
            or self.fb_error_pixels.shape != (h, w)
            or h * w > 1_048_576
            or min(h, w) <= 0
            or self.mapping.target_dimensions != (w, h)
            or self.mapping.camera_dimensions != (self.pair.width, self.pair.height)
            or self.mapping.camera_image_id != self.pair.camera_image_id
            or not np.isfinite(self.vectors).all()
            or not np.isfinite(self.fb_error_pixels).all()
            or (self.fb_error_pixels < 0).any()
            or not 0 <= self.started_ns <= self.completed_ns
        ):
            raise ValueError("Invalid dense flow")
        object.__setattr__(self, "vectors", frozen_float(self.vectors))
        object.__setattr__(self, "fb_error_pixels", frozen_float(self.fb_error_pixels))
        object.__setattr__(self, "valid", frozen_mask(self.valid))

    @property
    def identity(self) -> FrameIdentity:
        return self.pair.b

    def sparse(self, maximum: int = 512) -> SparseFlowObservation:
        if not 1 <= maximum <= 4096:
            raise ValueError("Invalid sample bound")
        h, w = self.valid.shape
        # Uniform bounded grid, independent of valid ordering/spatial clustering.
        step = max(1, int(np.ceil(np.sqrt(h * w / maximum))))
        y, x = np.mgrid[step // 2 : h : step, step // 2 : w : step]
        x, y = x.ravel()[:maximum], y.ravel()[:maximum]
        a = np.column_stack((x + 0.5, y + 0.5)).astype(np.float64)
        b = a + self.vectors[y, x]
        return SparseFlowObservation(
            self.pair,
            restore_points(self.mapping, a),
            restore_points(self.mapping, b),
            self.valid[y, x],
            self.fb_error_pixels[y, x],
            self.provenance,
            self.started_ns,
            self.completed_ns,
        )

    def summary(self) -> dict[str, object]:
        return {
            "kind": "DENSE",
            "pair": asdict(self.pair),
            "dimensions": self.mapping.target_dimensions,
            "valid_fraction": float(self.valid.mean()),
            "transform_hash": self.mapping.fingerprint,
            "vector_units": "PROCESSED_PIXELS_PER_PAIR",
            "provenance": asdict(self.provenance),
            "started_ns": self.started_ns,
            "completed_ns": self.completed_ns,
        }


def restore_points(mapping: ImageMapping, points: NDArray[np.float64]) -> NDArray[np.float64]:
    # Both endpoints are restored: translation offsets cancel, resize/rotation does not.
    origin = np.array(mapping.inverse(0, 0))
    basis = np.column_stack(
        (np.array(mapping.inverse(1, 0)) - origin, np.array(mapping.inverse(0, 1)) - origin)
    )
    return np.asarray(points @ basis.T + origin, dtype=np.float64)


FlowObservation = SparseFlowObservation | DenseFlowField


class OpticalFlowProvider(Protocol):
    provenance: ComponentProvenance

    def estimate(
        self, a: NDArray[np.uint8], b: NDArray[np.uint8], pair: FramePair, mapping: ImageMapping
    ) -> FlowObservation: ...
