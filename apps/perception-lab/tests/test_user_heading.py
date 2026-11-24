"""Camera optical axis is never silently accepted as user travel direction."""

from dataclasses import replace

import numpy as np
import pytest
from test_motion import camera as camera_fixture
from test_motion import scene

from perception_lab.contracts import ComponentProvenance
from perception_lab.motion import CameraMotionEstimate, MotionQuality, ScaleStatus
from perception_lab.user_heading import UserMotionHeadingEstimator

camera = camera_fixture


def motion_fixture(camera, translation):
    flow, _ = scene(camera)
    return CameraMotionEstimate(
        flow.pair,
        np.eye(3),
        np.array(translation, dtype=float),
        ScaleStatus.UP_TO_SCALE,
        MotionQuality("DEGRADED", "FIXTURE", 160, 140, 0.8, 0.9),
        ComponentProvenance("fixture", "motion"),
        0,
        1,
    )


@pytest.mark.parametrize(
    "translation,expected",
    [((1, 0, 0), (-1, 0, 0)), ((0, 0, 1), (0, 0, -1)), ((0, 0, -1), (0, 0, 1))],
)
def test_travel_sign_and_sideways_mount(camera, translation, expected):
    motion = motion_fixture(camera, translation)
    result = UserMotionHeadingEstimator().estimate(
        motion,
        motion.pair.b,
        "camera-B",
        rigid_mount_confirmed=True,
        ground_normal_camera=(0, 1, 0),
    )
    assert result.direction == expected
    assert result.quality == "DEGRADED"
    assert result.uncertainty == "UNQUANTIFIED"


def test_unconfirmed_mount_missing_ground_stale_or_vertical_are_unknown(camera):
    estimator = UserMotionHeadingEstimator()
    motion = motion_fixture(camera, (1, 0, 0))
    assert estimator.estimate(motion, motion.pair.b, "camera-B").direction is None
    assert (
        estimator.estimate(motion, motion.pair.b, "camera-B", rigid_mount_confirmed=True).direction
        is None
    )
    late = replace(motion.pair.b, observation_ns=motion.pair.b.observation_ns + 500_000_000)
    assert (
        estimator.estimate(
            motion, late, "camera-B", rigid_mount_confirmed=True, ground_normal_camera=(0, 1, 0)
        ).direction
        is None
    )
    vertical = motion_fixture(camera, (0, 1, 0))
    assert (
        estimator.estimate(
            vertical,
            vertical.pair.b,
            "camera-B",
            rigid_mount_confirmed=True,
            ground_normal_camera=(0, 1, 0),
        ).direction
        is None
    )


def test_no_motion_never_fabricates_camera_forward(camera):
    motion = motion_fixture(camera, (1, 0, 0))
    result = UserMotionHeadingEstimator().estimate(None, motion.pair.b, "camera-B")
    assert result.direction is None and result.quality == "UNKNOWN" and result.age_ns is None
