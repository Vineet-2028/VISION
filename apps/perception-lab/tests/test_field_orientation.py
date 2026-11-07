from math import pi

import pytest

from perception_lab.contracts import FrameIdentity, TimingProvenance
from perception_lab.field_orientation import field_orientation
from perception_lab.field_protocol import PROTOCOL, FrameHeader, PhoneSensors


def header():
    return FrameHeader(
        protocol_version=PROTOCOL,
        session_id="test",
        sequence=1,
        camera_ns="200000000",
        capture_ns="200000000",
        send_ns="200000000",
        sync_version=1,
        rotation=90,
        width=640,
        height=480,
        format="JPEG",
        jpeg_quality=75,
    )


@pytest.mark.parametrize(
    "stamp,gravity,source",
    [
        ("200000000", [0, 9.81, 0], "IMU"),
        ("99999999", [0, 9.81, 0], "CAMERA_METADATA"),
        ("200000001", [0, 9.81, 0], "CAMERA_METADATA"),
        ("200000000", [0, 0, 9.81], "CAMERA_METADATA"),
    ],
)
def test_gravity_maps_from_natural_axes_only_when_fresh_and_observable(stamp, gravity, source):
    identity = FrameIdentity("test", 1, 0, TimingProvenance.AUTHORITATIVE_PTS)
    state = field_orientation(
        identity,
        header().model_copy(
            update={
                "sensors": PhoneSensors(
                    mount_clockwise_degrees=90, gravity_ns=stamp, gravity_device=gravity
                )
            }
        ),
    )
    assert state.source == source and state.identity == identity
    assert state.yaw_radians is None and state.pitch_radians is None
    if source == "IMU":
        assert state.roll_radians == pytest.approx(-pi / 2)
    else:
        assert state.roll_radians is None and state.sensor_rotation_degrees == 90
