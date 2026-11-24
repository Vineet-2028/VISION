"""Travel heading can orient supplied-ground geometry; stale evidence cannot."""

from dataclasses import replace
from math import sqrt

import pytest
from test_corridor import analyzer, scene
from test_world_model import identity
from test_world_model import spatial as spatial_fixture

from perception_lab.contracts import ComponentProvenance
from perception_lab.user_heading import UserMotionHeadingEstimate

spatial = spatial_fixture


def heading(geometry):
    return UserMotionHeadingEstimate(
        identity(),
        geometry.c.camera_frame_id,
        (1 / sqrt(2), 0.0, 1 / sqrt(2)),
        "DEGRADED",
        "VISUAL_CAMERA_TRANSLATION_PROJECTED_ON_SUPPLIED_GROUND",
        0,
        "UNQUANTIFIED",
        ("RIGID_MOUNT_ASSUMPTION; VISUAL_DIRECTION_UNVALIDATED",),
        ComponentProvenance("user-motion-heading-v1", "heading-estimator"),
    )


def test_authorized_heading_changes_corridor_without_claiming_validated_geometry(spatial):
    state = scene(spatial, metric=True)
    baseline = analyzer(spatial).analyze(state)
    estimate = heading(spatial)
    result = analyzer(spatial).analyze(replace(state, user_motion_heading=estimate))
    assert result.corridor.forward == pytest.approx(estimate.direction)
    assert result.corridor.forward != baseline.corridor.forward
    assert result.corridor.heading_source == "USER_TRAVEL_DIRECTION"
    assert result.corridor.heading_evidence.provenance == (estimate.provenance,)
    assert result.corridor.quality == "DEGRADED"
    assert "PHYSICAL_GEOMETRY_UNVALIDATED" in result.corridor.reasons


@pytest.mark.parametrize(
    "change",
    [
        {"identity": identity(1)},
        {"coordinate_frame": "other-camera"},
        {"quality": "UNKNOWN"},
        {"source": "UNAVAILABLE"},
        {"age_ns": 1},
        {"direction": (float("nan"), 0.0, 1.0)},
        {"direction": (2.0, 0.0, 0.0)},
    ],
)
def test_unusable_heading_falls_back_explicitly_without_relabeling_camera_forward(spatial, change):
    state = scene(spatial, metric=True)
    baseline = analyzer(spatial).analyze(state)
    result = analyzer(spatial).analyze(
        replace(state, user_motion_heading=replace(heading(spatial), **change))
    )
    assert result.corridor.forward == baseline.corridor.forward
    assert result.corridor.heading_source == "CAMERA_FORWARD"
    assert "USER_HEADING_UNUSABLE" in result.corridor.reasons
    assert "CAMERA_FORWARD_NOT_BODY_HEADING" in result.corridor.reasons


def test_heading_without_ground_does_not_invent_metric_corridor(spatial):
    result = analyzer(spatial).analyze(
        replace(scene(spatial), user_motion_heading=heading(spatial))
    )
    assert result.corridor.forward is None
    assert result.corridor.heading_source == "CAMERA_FORWARD"
    assert "GROUND_PLANE_UNAVAILABLE" in result.corridor.reasons
