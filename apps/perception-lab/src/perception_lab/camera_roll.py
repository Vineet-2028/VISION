"""Explicit image-plane roll correction; pitch/yaw never become a 2D warp."""

from dataclasses import dataclass
from math import pi
from typing import Literal, cast

import cv2
import numpy as np
from numpy.typing import NDArray

from .camera_orientation import CameraOrientationState
from .contracts import Frame
from .geometry import CoreGeometry, ImageMapping
from .preprocessing import ModelInputDescriptor, PreparedImage


@dataclass(frozen=True)
class RollCanonicalFrame:
    prepared: PreparedImage
    orientation: CameraOrientationState
    correction_radians: float | None
    canvas: str
    status: str
    calibration_policy: str = "INVERSE_MAP_TO_ORIGINAL_CALIBRATION"


class RollCanonicalizer:
    """One-frame mapping cache; no quantization, unbounded history, or model loading.

    roll_radians means clockwise roll of the received image about its center.
    The adapter must already resolve sensor/display rotation into this convention.
    Caller retains cardinal handling separately; this method never applies it twice.
    """

    def __init__(
        self,
        geometry: CoreGeometry,
        canvas: Literal["EXPAND", "PAD", "CROP"] = "EXPAND",
        max_pixels: int = 16_000_000,
    ) -> None:
        if canvas not in {"EXPAND", "PAD", "CROP"} or type(max_pixels) is not int or max_pixels < 1:
            raise ValueError("Invalid roll canvas budget")
        self.geometry, self.canvas, self.max_pixels = geometry, canvas, max_pixels
        if geometry.source_mapping is not None:
            raise ValueError("Roll requires original calibrated source dimensions")
        self._last: tuple[float, ImageMapping] | None = None

    def canonicalize(self, frame: Frame, orientation: CameraOrientationState) -> RollCanonicalFrame:
        if orientation.identity != frame.identity:
            raise ValueError("Orientation belongs to another source frame")
        self.geometry.require_dimensions(frame.width, frame.height)
        available = (
            orientation.quality == "GOOD"
            and orientation.source in {"IMU", "SYNTHETIC_TEST"}
            and orientation.roll_radians is not None
        )
        angle = (
            -orientation.roll_radians if available and orientation.roll_radians is not None else 0.0
        )
        if not -pi <= angle <= pi:
            raise ValueError("Roll outside [-pi, pi]")
        if available:
            if self._last is None or self._last[0] != angle:
                self._last = (angle, self.geometry.roll_mapping(angle, self.canvas))
            mapping = self._last[1]
        else:
            mapping = self.geometry.mapping("identity", frame.width, frame.height)
        width, height = mapping.target_dimensions
        if width * height > self.max_pixels:
            raise ValueError("Roll canvas exceeds pixel budget")
        # Guardian uses continuous edges; OpenCV addresses pixel centers at integers.
        # Evaluate the same transform at source center (0.5, 0.5), then subtract
        # destination half-pixel. This avoids a half-pixel bias for nonzero roll.
        origin = mapping.forward(0.5, 0.5)
        x, y = mapping.forward(1.5, 0.5), mapping.forward(0.5, 1.5)
        matrix = np.array(
            [
                [x[0] - origin[0], y[0] - origin[0], origin[0] - 0.5],
                [x[1] - origin[1], y[1] - origin[1], origin[1] - 0.5],
            ],
            dtype=np.float64,
        )
        warped = (
            cv2.warpAffine(
                frame.pixels,
                matrix,
                (width, height),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=0,
            )
            if available
            else np.array(frame.pixels, copy=True)
        )
        # warpAffine preserves the input uint8 dtype; its stubs allow other inputs too.
        pixels = cast(NDArray[np.uint8], warped)
        if pixels.ndim == 2:
            pixels = pixels[:, :, None]
        pixels.flags.writeable = False
        return RollCanonicalFrame(
            PreparedImage(
                pixels,
                ModelInputDescriptor(
                    width, height, frame.pixel_format.channels, frame.pixel_format, "uint8", "NHWC"
                ),
                mapping,
            ),
            orientation,
            angle if available else None,
            self.canvas,
            "ROLL_CANONICALIZED" if available else "ORIENTATION_UNAVAILABLE",
        )
