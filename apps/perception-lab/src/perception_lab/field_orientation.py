"""Back-camera, timestamp-bound sensor mapping; camera roll never supplies user heading."""

from math import atan2, cos, hypot, radians, sin

from .camera_orientation import CameraOrientationState
from .contracts import FrameIdentity
from .field_protocol import FrameHeader


def field_orientation(identity: FrameIdentity, header: FrameHeader) -> CameraOrientationState:
    cardinal = CameraOrientationState(
        identity, header.rotation, "GOOD", "CAMERA_METADATA", "CameraX rotationDegrees"
    )
    sensors = header.sensors
    if sensors is None or sensors.gravity_ns is None or sensors.gravity_device is None:
        return cardinal
    if not 0 <= int(header.camera_ns) - int(sensors.gravity_ns) <= 100_000_000:
        return cardinal
    x, y, z = sensors.gravity_device
    if not 6 <= hypot(x, y, z) <= 14 or hypot(x, y) < 3:
        return cardinal
    # Android device +Y is up. The received rear-camera image has +Y down.
    # Undo its mount-to-natural clockwise correction before measuring image roll.
    angle = radians(-sensors.mount_clockwise_degrees)
    raw_x, raw_y = cos(angle) * x + sin(angle) * y, sin(angle) * x - cos(angle) * y
    return CameraOrientationState(
        identity,
        header.rotation,
        "GOOD",
        "IMU",
        "timestamped rear-camera gravity projection",
        gravity_vector_device=(x, y, z),
        gravity_vector_camera=(raw_x, raw_y, -z),
        roll_radians=atan2(raw_x, -raw_y),
    )
