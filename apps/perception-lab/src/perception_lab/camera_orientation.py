"""Timestamp-bound camera orientation. Cardinal math delegates to Guardian Task003."""

from dataclasses import dataclass
from math import isfinite
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from .contracts import Frame, FrameIdentity
from .geometry import CoreGeometry, ImageMapping
from .preprocessing import ModelInputDescriptor, PreparedImage


@dataclass(frozen=True)
class CameraOrientationState:
    identity: FrameIdentity
    sensor_rotation_degrees: Literal[0, 90, 180, 270] | None
    quality: Literal["GOOD", "DEGRADED", "UNKNOWN"]
    source: Literal["CAMERA_METADATA", "IMU", "SYNTHETIC_TEST", "UNKNOWN"]
    provenance: str
    gravity_vector_device: tuple[float, float, float] | None = None
    gravity_vector_camera: tuple[float, float, float] | None = None
    roll_radians: float | None = None
    pitch_radians: float | None = None
    yaw_radians: float | None = None

    def __post_init__(self) -> None:
        if self.sensor_rotation_degrees is not None and (
            type(self.sensor_rotation_degrees) is not int
            or self.sensor_rotation_degrees not in (0, 90, 180, 270)
        ):
            raise ValueError("Invalid cardinal rotation")
        if self.quality not in ("GOOD", "DEGRADED", "UNKNOWN") or self.source not in (
            "CAMERA_METADATA",
            "IMU",
            "SYNTHETIC_TEST",
            "UNKNOWN",
        ):
            raise ValueError("Invalid orientation quality/provenance")
        if not 1 <= len(self.provenance) <= 128:
            raise ValueError("Orientation provenance required")
        values = (self.roll_radians, self.pitch_radians, self.yaw_radians)
        if any(v is not None and not isfinite(v) for v in values):
            raise ValueError("Nonfinite orientation")
        for vector in (self.gravity_vector_camera, self.gravity_vector_device):
            if vector is not None and (
                not isinstance(vector, tuple)
                or len(vector) != 3
                or not all(isfinite(v) for v in vector)
                or sum(v * v for v in vector) <= 1e-12
            ):
                raise ValueError("Invalid gravity vector")
        if self.source == "UNKNOWN" and (
            self.quality != "UNKNOWN"
            or self.sensor_rotation_degrees is not None
            or any(v is not None for v in values)
            or self.gravity_vector_camera is not None
            or self.gravity_vector_device is not None
        ):
            raise ValueError("Unknown source cannot fabricate orientation evidence")


@dataclass(frozen=True)
class CanonicalCameraFrame:
    identity: FrameIdentity
    pixels: NDArray[np.uint8]
    source_to_canonical: ImageMapping
    ideal_intrinsics_fx_fy_cx_cy: tuple[float, float, float, float]
    original_to_canonical_camera_basis: tuple[float, ...]
    orientation: CameraOrientationState
    calibration_quality: str
    status: Literal["CARDINAL_CANONICALIZED", "ORIENTATION_UNAVAILABLE"]
    distortion_policy: Literal["INVERSE_MAP_TO_ORIGINAL_CALIBRATION"] = (
        "INVERSE_MAP_TO_ORIGINAL_CALIBRATION"
    )


class CameraCanonicalizer:
    def __init__(self, geometry: CoreGeometry) -> None:
        self.geometry = geometry
        self.mappings = tuple(geometry.cardinal_geometry(q) for q in range(4))

    def prepare(self, frame: Frame, orientation: CameraOrientationState) -> PreparedImage:
        """Use existing detector preprocessing while retaining the original camera mapping.

        Vendor adapters may letterbox/resize this image and compose that transform.
        Their inverse-mapped detections therefore still occupy original camera coordinates.
        """
        canonical = self.canonicalize(frame, orientation)
        height, width = canonical.pixels.shape[:2]
        return PreparedImage(
            canonical.pixels,
            ModelInputDescriptor(
                width, height, frame.pixel_format.channels, frame.pixel_format, "uint8", "NHWC"
            ),
            canonical.source_to_canonical,
        )

    def canonicalize(
        self, frame: Frame, orientation: CameraOrientationState
    ) -> CanonicalCameraFrame:
        if frame.identity != orientation.identity:
            raise ValueError("Orientation belongs to another source frame")
        self.geometry.require_dimensions(frame.width, frame.height)
        available = (
            orientation.quality == "GOOD" and orientation.sensor_rotation_degrees is not None
        )
        turns = (
            orientation.sensor_rotation_degrees // 90
            if available and orientation.sensor_rotation_degrees is not None
            else 0
        )
        mapping, intrinsics, basis = self.mappings[turns]
        # np.rot90 works on pixel centers; Guardian maps the corresponding continuous edges.
        pixels = np.ascontiguousarray(np.rot90(frame.pixels, -turns, axes=(0, 1)))
        pixels.flags.writeable = False
        return CanonicalCameraFrame(
            frame.identity,
            pixels,
            mapping,
            intrinsics,
            basis,
            orientation,
            self.geometry.c.calibration_quality.state,
            "CARDINAL_CANONICALIZED" if available else "ORIENTATION_UNAVAILABLE",
        )
