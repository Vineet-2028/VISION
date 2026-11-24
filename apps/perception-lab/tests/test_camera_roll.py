"""Roll pixels and continuous-edge mappings agree; unavailable metadata is inert."""

from dataclasses import replace
from math import radians

import numpy as np
import pytest
from test_camera_orientation import image

from perception_lab.camera_orientation import CameraOrientationState
from perception_lab.camera_roll import RollCanonicalizer
from perception_lab.contracts import PixelFormat


def orientation(frame, degrees):
    return CameraOrientationState(
        frame.identity,
        0,
        "GOOD",
        "SYNTHETIC_TEST",
        "roll-fixture",
        roll_radians=radians(degrees),
    )


@pytest.mark.parametrize("canvas", ["EXPAND", "PAD", "CROP"])
@pytest.mark.parametrize("degrees", [-60, -45, -30, -20, -15, -10, 10, 15, 20, 30, 45, 60])
def test_arbitrary_roll_inverse_and_detector_resize_chain(geometry, canvas, degrees):
    frame = image(geometry)
    result = RollCanonicalizer(geometry, canvas).canonicalize(frame, orientation(frame, degrees))
    prepared = result.prepared
    mapping, _ = prepared.mapping.letterboxed(416, 416)
    for point in ((0.5, 0.5), (frame.width / 2, frame.height / 2), (123.25, 89.5)):
        assert mapping.inverse(*mapping.forward(*point)) == pytest.approx(point)
    assert prepared.pixels.shape == (prepared.descriptor.height, prepared.descriptor.width, 3)
    assert not prepared.pixels.flags.writeable
    assert result.correction_radians == -radians(degrees)
    assert result.calibration_policy == "INVERSE_MAP_TO_ORIGINAL_CALIBRATION"


def test_quarter_roll_pixels_match_cardinal_rotation_without_half_pixel_bias(geometry):
    frame = image(geometry)
    result = RollCanonicalizer(geometry, "CROP").canonicalize(frame, orientation(frame, 180))
    np.testing.assert_array_equal(result.prepared.pixels, np.rot90(frame.pixels, 2))


@pytest.mark.parametrize("degrees", [-45, -15, 15, 45, 90])
def test_pixel_peak_matches_continuous_edge_mapping_at_arbitrary_roll(geometry, degrees):
    frame = image(geometry)
    pixels = np.zeros_like(frame.pixels)
    pixels[1, 2] = 255
    frame = replace(frame, pixels=pixels)
    result = RollCanonicalizer(geometry).canonicalize(frame, orientation(frame, degrees))
    u, v = result.prepared.mapping.forward(2.5, 1.5)
    y, x = np.unravel_index(
        np.argmax(result.prepared.pixels[:, :, 0]), result.prepared.pixels.shape[:2]
    )
    assert abs((x + 0.5) - u) <= 1
    assert abs((y + 0.5) - v) <= 1
    if degrees == 90:
        np.testing.assert_array_equal(result.prepared.pixels, np.rot90(frame.pixels))


def test_gray_roll_retains_channel_axis_and_unknown_roll_never_uses_pitch_yaw(geometry):
    frame = image(geometry)
    gray = replace(frame, pixels=frame.pixels[:, :, :1].copy(), pixel_format=PixelFormat.GRAY)
    result = RollCanonicalizer(geometry).canonicalize(gray, orientation(gray, 30))
    assert result.prepared.pixels.shape[2] == 1
    unknown = replace(orientation(frame, 30), roll_radians=None, pitch_radians=0.5, yaw_radians=0.4)
    result = RollCanonicalizer(geometry).canonicalize(frame, unknown)
    assert result.status == "ORIENTATION_UNAVAILABLE" and result.correction_radians is None
    np.testing.assert_array_equal(result.prepared.pixels, frame.pixels)


def test_roll_rejects_wrong_frame_and_excessive_canvas_before_allocation(geometry):
    frame = image(geometry)
    metadata = orientation(frame, 45)
    with pytest.raises(ValueError, match="another source frame"):
        RollCanonicalizer(geometry).canonicalize(
            frame, replace(metadata, identity=replace(frame.identity, sequence=99))
        )
    with pytest.raises(ValueError, match="pixel budget"):
        RollCanonicalizer(geometry, max_pixels=1).canonicalize(frame, metadata)
