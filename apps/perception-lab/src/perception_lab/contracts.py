"""Small immutable observation/results contracts; buffers have explicit ownership."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from .components import DepthOutput, DetectionOutput, OpticalFlowOutput, SegmentationOutput
    from .depth_sampling import DepthEstimate, TrackDepthObservation
    from .motion import CameraMotionEstimate, TrackImageMotionObservation
    from .tracking_types import TrackSet


class SourceType(StrEnum):
    VIDEO_FILE = "VIDEO_FILE"
    IMAGE_SEQUENCE = "IMAGE_SEQUENCE"
    LIVE_CAMERA = "LIVE_CAMERA"
    RECORDED_SESSION = "RECORDED_SESSION"


class PixelFormat(StrEnum):
    RGB = "RGB"
    BGR = "BGR"
    GRAY = "GRAY"
    RGBA = "RGBA"

    @property
    def channels(self) -> int:
        return {self.RGB: 3, self.BGR: 3, self.GRAY: 1, self.RGBA: 4}[self]


class TimingProvenance(StrEnum):
    AUTHORITATIVE_PTS = "AUTHORITATIVE_PTS"
    DERIVED_FROM_RATE = "DERIVED_FROM_RATE"
    SYNTHETIC = "SYNTHETIC"
    UNKNOWN = "UNKNOWN"


class DropReason(StrEnum):
    QUEUE_OVERFLOW = "QUEUE_OVERFLOW"
    REALTIME_STALENESS = "REALTIME_STALENESS"
    INVALID_TIMESTAMP = "INVALID_TIMESTAMP"
    DECODE_FAILURE = "DECODE_FAILURE"
    CORRUPT_FRAME = "CORRUPT_FRAME"
    PIPELINE_FAILURE = "PIPELINE_FAILURE"
    USER_SKIP = "USER_SKIP"


class FailureSeverity(StrEnum):
    RECOVERABLE = "RECOVERABLE"
    FATAL = "FATAL"


class LabError(Exception):
    """Only a public error code, never a decoder's filename-bearing message."""

    def __init__(self, code: str, severity: FailureSeverity = FailureSeverity.FATAL) -> None:
        super().__init__(code)
        self.code = code
        self.severity = severity


@dataclass(frozen=True)
class FrameIdentity:
    source_id: str
    sequence: int
    observation_ns: int
    timing: TimingProvenance

    def __post_init__(self) -> None:
        if not self.source_id or self.sequence < 0 or not 0 <= self.observation_ns <= 2**63 - 1:
            raise ValueError("Invalid frame identity")


@dataclass(frozen=True)
class Frame:
    identity: FrameIdentity
    pixels: NDArray[np.uint8]
    pixel_format: PixelFormat
    decode_started_ns: int
    decode_completed_ns: int
    conversion_ns: int = 0
    wall_clock_epoch_ms: int | None = None

    def __post_init__(self) -> None:
        if (
            self.pixels.dtype != np.uint8
            or self.pixels.ndim != 3
            or self.pixels.shape[2] != self.pixel_format.channels
            or min(self.pixels.shape) <= 0
            or self.decode_completed_ns < self.decode_started_ns
            or self.conversion_ns < 0
        ):
            raise ValueError("Invalid frame buffer/timing")
        self.pixels.flags.writeable = False

    @property
    def width(self) -> int:
        return int(self.pixels.shape[1])

    @property
    def height(self) -> int:
        return int(self.pixels.shape[0])


@dataclass(frozen=True)
class SourceIssue:
    sequence: int
    reason: DropReason


@dataclass(frozen=True)
class FrameTimingTrace:
    """All fields except observation identity use the process monotonic clock."""

    decode_started_ns: int
    decode_completed_ns: int
    pipeline_accepted_ns: int
    preprocess_started_ns: int
    preprocess_completed_ns: int
    component_started_ns: int
    component_completed_ns: int
    postprocess_completed_ns: int


@dataclass(frozen=True)
class ComponentProvenance:
    name: str
    component_type: str
    model_id: str | None = None
    model_version: str | None = None
    runtime: str | None = None
    configuration_hash: str | None = None


@dataclass(frozen=True)
class ComponentExecution:
    identity: FrameIdentity
    provenance: ComponentProvenance
    started_ns: int
    completed_ns: int
    status: str
    overrun_ns: int = 0


@dataclass(frozen=True)
class FrameResult:
    identity: FrameIdentity
    width: int
    height: int
    pixel_format: PixelFormat
    timing: FrameTimingTrace
    components: tuple[ComponentExecution, ...]
    # No-op adapters yield unavailable outputs, not empty invented measurements.
    detector: DetectionOutput | None = None
    depth: DepthOutput | None = None
    segmentation: SegmentationOutput | None = None
    optical_flow: OpticalFlowOutput | None = None
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    tracks: TrackSet | None = None
    detection_depths: tuple[DepthEstimate | None, ...] = ()
    track_depths: tuple[TrackDepthObservation, ...] = ()
    camera_motion: CameraMotionEstimate | None = None
    track_image_motion: tuple[TrackImageMotionObservation, ...] = ()


@dataclass(frozen=True)
class Event:
    kind: str
    identity: FrameIdentity | None = None
    reason: DropReason | None = None
    component: str | None = None
    sequence: int | None = None


class Listener(Protocol):
    def __call__(self, event: Event) -> None: ...


@dataclass
class Cancellation:
    # Pipeline is single-owner; external callers may request cancellation between steps.
    requested: bool = field(default=False)

    def cancel(self) -> None:
        self.requested = True
