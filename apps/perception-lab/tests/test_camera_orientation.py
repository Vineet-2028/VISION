from dataclasses import replace

import numpy as np
import pytest

from perception_lab.camera_orientation import CameraCanonicalizer, CameraOrientationState
from perception_lab.contracts import Frame, FrameIdentity, PixelFormat, TimingProvenance


def image(geometry):
    pixels = np.zeros((geometry.source_height, geometry.source_width, 3), dtype=np.uint8)
    pixels[0, 0] = [1, 2, 3]
    return Frame(
        FrameIdentity("fixture", 1, 123, TimingProvenance.SYNTHETIC), pixels, PixelFormat.RGB, 1, 2
    )


@pytest.mark.parametrize("degrees", [0, 90, 180, 270])
def test_cardinal_pixels_points_intrinsics_and_camera_basis_agree(geometry, degrees):
    frame = image(geometry)
    state = CameraOrientationState(frame.identity, degrees, "GOOD", "SYNTHETIC_TEST", "fixture")
    result = CameraCanonicalizer(geometry).canonicalize(frame, state)
    assert result.identity == frame.identity
    assert np.array_equal(result.pixels, np.rot90(frame.pixels, -degrees // 90))
    for x, y in [(0, 0), (frame.width, frame.height), (10.25, 20.5)]:
        assert result.source_to_canonical.inverse(
            *result.source_to_canonical.forward(x, y)
        ) == pytest.approx((x, y))
    intrinsics = geometry.c.intrinsics
    fx, fy, cx, cy = result.ideal_intrinsics_fx_fy_cx_cy
    assert (fx, fy) == (
        (intrinsics.fy, intrinsics.fx) if degrees in (90, 270) else (intrinsics.fx, intrinsics.fy)
    )
    assert (cx, cy) == pytest.approx(
        result.source_to_canonical.forward(intrinsics.cx, intrinsics.cy)
    )
    basis = np.array(result.original_to_canonical_camera_basis).reshape(3, 3)
    assert np.allclose(basis @ basis.T, np.eye(3))
    assert np.linalg.det(basis) == pytest.approx(1)
    assert not result.pixels.flags.writeable


def test_unknown_or_poor_orientation_does_not_rotate_or_invent_angles(geometry):
    frame = image(geometry)
    state = CameraOrientationState(frame.identity, None, "UNKNOWN", "UNKNOWN", "unavailable")
    result = CameraCanonicalizer(geometry).canonicalize(frame, state)
    assert np.array_equal(result.pixels, frame.pixels)
    assert result.status == "ORIENTATION_UNAVAILABLE" and state.yaw_radians is None
    with pytest.raises(ValueError):
        replace(state, yaw_radians=0)


def test_orientation_cannot_cross_frame_identity(geometry):
    frame = image(geometry)
    state = CameraOrientationState(
        replace(frame.identity, sequence=2), 90, "GOOD", "SYNTHETIC_TEST", "fixture"
    )
    with pytest.raises(ValueError, match="another source frame"):
        CameraCanonicalizer(geometry).canonicalize(frame, state)


@pytest.mark.parametrize("degrees", [0, 90, 180, 270])
def test_detector_resize_chain_returns_original_camera_coordinates(geometry, degrees):
    frame = image(geometry)
    state = CameraOrientationState(frame.identity, degrees, "GOOD", "SYNTHETIC_TEST", "fixture")
    prepared = CameraCanonicalizer(geometry).prepare(frame, state)
    assert (prepared.descriptor.height, prepared.descriptor.width) == prepared.pixels.shape[:2]
    mapping, _ = prepared.mapping.letterboxed(416, 416)
    for x, y in [(11.25, 37.75), (200.5, 100.5), (frame.width, frame.height)]:
        assert mapping.inverse(*mapping.forward(x, y)) == pytest.approx((x, y))
    assert prepared.mapping.camera_dimensions == (frame.width, frame.height)


@pytest.mark.parametrize("degrees", [False, 90.0, 45])
def test_cardinal_metadata_requires_integer_right_angles(geometry, degrees):
    with pytest.raises(ValueError, match="rotation"):
        CameraOrientationState(
            image(geometry).identity, degrees, "GOOD", "SYNTHETIC_TEST", "fixture"
        )
