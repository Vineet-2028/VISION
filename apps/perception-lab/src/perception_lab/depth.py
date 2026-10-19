"""Model-independent depth values. Relative ordering is never a metric measurement."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

import numpy as np
from numpy.typing import NDArray

from .contracts import ComponentProvenance, FrameIdentity, TimingProvenance
from .geometry import ImageMapping


class DepthKind(StrEnum):
    RELATIVE = "RELATIVE"
    METRIC = "METRIC"


class DepthDirection(StrEnum):
    LARGER_IS_FARTHER = "LARGER_IS_FARTHER"
    LARGER_IS_NEARER = "LARGER_IS_NEARER"


class DepthAxis(StrEnum):
    NONE = "NONE"
    CAMERA_Z = "CAMERA_Z"
    RAY_RANGE = "RAY_RANGE"


@dataclass(frozen=True)
class DepthRepresentation:
    kind: DepthKind
    direction: DepthDirection
    axis: DepthAxis = DepthAxis.NONE
    minimum: float | None = None
    maximum: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, DepthKind) or not isinstance(self.direction, DepthDirection):
            raise ValueError("Explicit depth enums required")
        if not isinstance(self.axis, DepthAxis):
            raise ValueError("Explicit depth axis required")
        if self.kind == DepthKind.METRIC:
            if self.axis == DepthAxis.NONE or self.direction != DepthDirection.LARGER_IS_FARTHER:
                raise ValueError("Metric output must be positive Z or range in meters")
        elif self.axis != DepthAxis.NONE:
            raise ValueError("Relative output has no metric axis")
        for value in (self.minimum, self.maximum):
            if value is not None and not isfinite(value):
                raise ValueError("Non-finite supported range")
        if self.minimum is not None and self.maximum is not None and self.minimum >= self.maximum:
            raise ValueError("Invalid supported range")

    @property
    def unit(self) -> str:
        return "METERS" if self.kind == DepthKind.METRIC else "NONE"

    @property
    def source(self) -> str:
        return "MODEL_ESTIMATED_METRIC_DEPTH" if self.kind == DepthKind.METRIC else "RELATIVE_DEPTH"


@dataclass(frozen=True, eq=False)
class DepthFrame:
    identity: FrameIdentity
    representation: DepthRepresentation
    values: NDArray[np.float32]
    valid: NDArray[np.bool_]
    mapping: ImageMapping
    provenance: ComponentProvenance
    started_ns: int
    completed_ns: int
    quality: NDArray[np.float32] | None = None

    def __post_init__(self) -> None:
        if self.identity.timing == TimingProvenance.UNKNOWN:
            raise ValueError("Depth requires known observation timing provenance")
        if (
            self.values.dtype != np.float32
            or self.values.ndim != 2
            or min(self.values.shape) < 1
            or self.valid.dtype != np.bool_
            or self.valid.shape != self.values.shape
            or self.started_ns < 0
            or self.completed_ns < self.started_ns
        ):
            raise ValueError("Invalid depth shape, dtype or timing")
        if self.mapping.target_dimensions != (self.width, self.height):
            raise ValueError("Depth transform dimensions disagree")
        r = self.representation
        valid = self.valid & np.isfinite(self.values)
        if r.kind == DepthKind.METRIC:
            valid &= self.values > 0
        if r.minimum is not None:
            valid &= self.values >= r.minimum
        if r.maximum is not None:
            valid &= self.values <= r.maximum
        # One immutable ownership copy per map, never per object. Bytes-backed arrays
        # cannot be made writable through a retained caller alias or setflags().
        safe = np.where(valid, self.values, 0).astype(np.float32, copy=False)
        object.__setattr__(
            self, "values", np.frombuffer(safe.tobytes(), np.float32).reshape(safe.shape)
        )
        object.__setattr__(
            self, "valid", np.frombuffer(valid.tobytes(), np.bool_).reshape(valid.shape)
        )
        if self.quality is not None:
            q = self.quality
            if q.shape != safe.shape or not np.all(np.isfinite(q) & (q >= 0) & (q <= 1)):
                raise ValueError("Invalid quality map; quality is not calibrated probability")
            object.__setattr__(
                self,
                "quality",
                np.frombuffer(q.astype(np.float32).tobytes(), np.float32).reshape(q.shape),
            )

    @property
    def width(self) -> int:
        return int(self.values.shape[1])

    @property
    def height(self) -> int:
        return int(self.values.shape[0])

    def summary(self) -> dict[str, object]:
        from dataclasses import asdict

        return {
            "identity": asdict(self.identity),
            "representation": asdict(self.representation),
            "unit": self.representation.unit,
            "source": self.representation.source,
            "width": self.width,
            "height": self.height,
            "valid_fraction": float(np.count_nonzero(self.valid) / self.valid.size),
            "provenance": asdict(self.provenance),
            "transform_hash": self.mapping.fingerprint,
            "started_ns": self.started_ns,
            "completed_ns": self.completed_ns,
        }
