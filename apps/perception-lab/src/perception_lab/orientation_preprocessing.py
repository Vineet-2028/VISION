"""Frame-bound orientation at the existing model-input boundary."""

from dataclasses import replace

from .camera_orientation import CameraCanonicalizer
from .camera_roll import RollCanonicalizer
from .config import LabConfig
from .contracts import Frame
from .geometry import CoreGeometry
from .preprocessing import BasicPreprocessor, ImagePreprocessor, PreparedImage


class OrientationPreprocessor:
    """Total received-image roll takes precedence over cardinal correction metadata.

    Roll is not added to cardinal rotation: an IMU adapter must express its total
    roll in received-image coordinates. Neither pitch nor yaw is used as image roll.
    All detections inverse-map to the unchanged original calibrated camera frame.
    """

    def __init__(self, geometry: CoreGeometry, config: LabConfig) -> None:
        if config.preprocess.operation != "identity" or config.preprocess.layout != "NHWC":
            raise ValueError("Orientation requires identity NHWC preprocessing")
        self.base = BasicPreprocessor(geometry, config.preprocess)
        self.cardinal = CameraCanonicalizer(geometry)
        self.roll = RollCanonicalizer(geometry, "EXPAND", max_pixels=config.max_pixels)

    def prepare(self, frame: Frame) -> PreparedImage:
        prepared = self.base.prepare(frame)
        orientation = frame.camera_orientation
        if orientation is None or orientation.quality != "GOOD":
            return prepared
        converted = replace(
            frame, pixels=prepared.pixels, pixel_format=prepared.descriptor.pixel_format
        )
        if orientation.source in {"IMU", "SYNTHETIC_TEST"} and orientation.roll_radians is not None:
            return self.roll.canonicalize(converted, orientation).prepared
        return self.cardinal.prepare(converted, orientation)


def build_preprocessor(geometry: CoreGeometry, config: LabConfig) -> ImagePreprocessor:
    if config.orientation_canonicalization:
        return OrientationPreprocessor(geometry, config)
    return BasicPreprocessor(geometry, config.preprocess)
