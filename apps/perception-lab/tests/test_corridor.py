import json
from dataclasses import FrozenInstanceError, asdict, replace
from math import copysign, cos, hypot, sin

import numpy as np
import pytest
from conftest import records
from test_world_model import depth, identity, model, tracks
from test_world_model import spatial as spatial_fixture

from perception_lab.contracts import ComponentProvenance
from perception_lab.corridor import (
    HybridCorridorAnalyzer,
    _polygon_edges,
    clip_rect,
    image_distance,
)
from perception_lab.corridor_config import CorridorConfig
from perception_lab.corridor_overlay import draw_corridor
from perception_lab.corridor_types import CorridorMode, Relation
from perception_lab.depth_sampling import track_depth
from perception_lab.depth_spatial import SuppliedDepthPose
from perception_lab.detection import Box, ObjectClass
from perception_lab.sources import SyntheticSource
from perception_lab.world_types import (
    EvidenceSource,
    EvidenceStatus,
    SuppliedGroundPlane,
    WorldImageGeometry,
)

spatial = spatial_fixture


def test_prepared_polygon_distance_matches_analytic_rectangle_in_both_windings():
    polygon = ((0.0, 0.0), (4.0, 0.0), (4.0, 3.0), (0.0, 3.0))
    for winding in (polygon, tuple(reversed(polygon))):
        for x in (-10.0, -1.0, 0.0, 0.5, 2.0, 4.0, 5.0, 100.0):
            for y in (-5.0, 0.0, 1.0, 3.0, 8.0):
                expected = (
                    -min(x, 4 - x, y, 3 - y)
                    if 0 <= x <= 4 and 0 <= y <= 3
                    else hypot(max(0.0, -x, x - 4), max(0.0, -y, y - 3))
                )
                actual = image_distance((x, y), winding)
                assert actual == expected
                if actual == 0:
                    assert copysign(1.0, actual) == -1.0


def test_polygon_preparation_cache_is_bounded_and_retains_no_point_observations():
    _polygon_edges.cache_clear()
    for shift in range(100):
        polygon = ((float(shift), 0.0), (shift + 1.0, 0.0), (float(shift), 1.0))
        image_distance((0.25, 0.25), polygon)
    assert _polygon_edges.cache_info().currsize == 32
    for x in range(1000):
        image_distance((float(x), 0.5), polygon)
    assert _polygon_edges.cache_info().currsize == 32
    _polygon_edges.cache_clear()
    large_polygon = tuple((cos(i / 100), sin(i / 100)) for i in range(100))
    image_distance((0.0, 0.0), large_polygon)
    assert _polygon_edges.cache_info().currsize == 0


def evidence(t=0, status=EvidenceStatus.FRESH):
    return EvidenceSource(
        "camera",
        identity(t),
        0,
        status,
        "OBSERVED",
        "DEGRADED",
        "UNVERIFIED",
        (ComponentProvenance("fixture", "camera"),),
    )


def scene(g, count=1, metric=False, world=False):
    w = model(g)
    ts = tracks(count=count)
    w.ingest_tracks(ts, 0)
    if metric:
        w.ingest_depth(track_depth(ts, depth(g))[0], 0)
    if world:
        w.ingest_pose(
            "test",
            SuppliedDepthPose(
                identity(), "device", "local-world", (0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)
            ),
            ComponentProvenance("pose", "pose"),
            0,
            "SYNTHETIC",
        )
    state = w.snapshot(0)
    state = replace(state, image_geometry=WorldImageGeometry(g.c.image_frame_id, 8, 6, evidence()))
    if metric:
        state = replace(
            state,
            ground_plane=SuppliedGroundPlane(
                "LOCAL_WORLD" if world else "CAMERA",
                "local-world" if world else g.c.camera_frame_id,
                (0.0, 1.0, 0.0),
                (0.0, -1.0, 0.0),
                evidence(),
            ),
        )
    return state


def analyzer(g=None, **kwargs):
    return HybridCorridorAnalyzer(CorridorConfig(**kwargs), g)


def test_image_fallback_immutable_and_no_entity_removal(geometry):
    s = scene(geometry, 10)
    before = asdict(s)
    a = analyzer().analyze(s)
    assert a.corridor.mode == CorridorMode.IMAGE
    assert len(a.entity_relations) == 10 and asdict(s) == before
    assert a.corridor.near_distance_m is None
    assert a.surface_evidence.quality == "UNAVAILABLE"
    assert a.free_space_evidence.unknown_fraction == 1
    assert "UNKNOWN" in a.free_space_evidence.states
    assert analyzer().analyze(s) == a
    with pytest.raises(FrozenInstanceError):
        a.quality = "GOOD"
    assert json.loads(json.dumps(asdict(a)))["schema_version"] == 1


@pytest.mark.parametrize(
    "x,z,expected",
    [
        (0, 3, Relation.INSIDE),
        (0.96, 3, Relation.NEAR_BOUNDARY),
        (1, 3, Relation.NEAR_BOUNDARY),
        (-2, 3, Relation.OUTSIDE),
        (2, 3, Relation.OUTSIDE),
        (0, 0.25, Relation.OUTSIDE),
        (0, 6, Relation.OUTSIDE),
    ],
)
def test_analytical_metric_relations(spatial, x, z, expected):
    s = scene(spatial, metric=True)
    e = s.entities[0]
    e = replace(
        e, position_camera=replace(e.position_camera, position_meters=(float(x), 1.0, float(z)))
    )
    s = replace(s, entities=(e,))
    a = analyzer(
        spatial, near_m=1.0, far_m=5.0, near_half_width_m=1.0, far_half_width_m=1.0
    ).analyze(s)
    r = a.entity_relations[0]
    assert a.corridor.mode == CorridorMode.GROUND
    assert r.relation == expected
    assert r.forward_distance_m == pytest.approx(z)
    assert r.lateral_offset_m == pytest.approx(x)
    assert r.signed_boundary_distance_m is not None
    assert "POINT_NOT_PHYSICAL_FOOTPRINT" in r.assumptions


def test_world_corridor_matches_pose_and_translation(spatial):
    s = scene(spatial, metric=True, world=True)
    a = analyzer(spatial, far_m=6.0).analyze(s)
    assert a.corridor.mode == CorridorMode.WORLD
    assert a.corridor.origin == pytest.approx((1, 1, 0))
    assert a.entity_relations[0].lateral_offset_m == pytest.approx(0)
    assert a.entity_relations[0].forward_distance_m == pytest.approx(5)
    assert a.corridor.heading_source == "POSE_CAMERA_FORWARD"


@pytest.mark.parametrize(
    "change",
    [
        "pose_time",
        "pose_frame",
        "quaternion",
        "calibration",
        "plane_clock",
        "plane_frame",
        "plane_missing",
        "plane_nonfinite",
    ],
)
def test_invalid_metric_inputs_fall_back(spatial, change):
    s = scene(spatial, metric=True, world=True)
    cam, plane = s.camera_state, s.ground_plane
    if change == "pose_time":
        cam = replace(cam, pose=replace(cam.pose, identity=identity(1)))
    if change == "pose_frame":
        cam = replace(cam, pose=replace(cam.pose, world_frame_id="other"))
    if change == "quaternion":
        cam = replace(cam, pose=replace(cam.pose, rotation_wxyz=(2.0, 0.0, 0.0, 0.0)))
    if change == "calibration":
        cam = replace(cam, calibration_quality="UNKNOWN")
    if change == "plane_clock":
        plane = replace(
            plane, evidence=replace(plane.evidence, identity=replace(identity(), source_id="other"))
        )
    if change == "plane_frame":
        plane = replace(plane, coordinate_frame="DEVICE")
    if change == "plane_missing":
        plane = None
    if change == "plane_nonfinite":
        plane = replace(plane, normal=(float("nan"), 0.0, 0.0))
    a = analyzer(spatial).analyze(replace(s, camera_state=cam, ground_plane=plane))
    assert a.corridor.mode == CorridorMode.IMAGE


@pytest.mark.parametrize("angle", [0, 0.1, 1.57, 3.14, -1.57])
def test_rapid_pose_turn_is_current_and_finite(spatial, angle):
    s = scene(spatial, metric=True, world=True)
    pose = replace(s.camera_state.pose, rotation_wxyz=(cos(angle / 2), 0.0, sin(angle / 2), 0.0))
    s = replace(s, camera_state=replace(s.camera_state, pose=pose))
    a = analyzer(spatial).analyze(s)
    assert a.corridor.forward == pytest.approx((sin(angle), 0, cos(angle)))
    json.dumps(asdict(a), allow_nan=False)


def test_surface_unknown_and_occupied_remain_evidence(geometry):
    s = scene(geometry, count=0)
    surface = replace(
        s.surface_state,
        evidence=evidence(),
        camera_image_id=geometry.c.image_frame_id,
        dimensions=(8, 6),
        samples=((3.5, 4.5, 6), (4.5, 4.5, 1), (3.5, 5.5, 8), (4.5, 5.5, 0)),
    )
    a = analyzer().analyze(replace(s, surface_state=surface))
    assert a.surface_evidence.sample_count == 4
    assert a.surface_evidence.candidate_ground_fraction == 0.25
    assert a.surface_evidence.unknown_fraction == 0.5
    assert a.surface_evidence.obstacle_evidence_fraction == 0.25
    assert a.surface_evidence.validation_status == "UNVERIFIED"
    assert a.free_space_evidence.states == ("UNKNOWN", "AVAILABLE_EVIDENCE", "OCCUPIED_EVIDENCE")


@pytest.mark.parametrize(
    "status",
    [
        EvidenceStatus.STALE,
        EvidenceStatus.FAILED,
        EvidenceStatus.PROPAGATED,
        EvidenceStatus.UNAVAILABLE,
    ],
)
def test_stale_surface_does_not_become_current(geometry, status):
    s = scene(geometry)
    surface = replace(
        s.surface_state,
        evidence=evidence(status=status),
        camera_image_id=geometry.c.image_frame_id,
        dimensions=(8, 6),
        samples=((4.0, 5.0, 6),),
    )
    a = analyzer().analyze(replace(s, surface_state=surface))
    assert a.surface_evidence.unknown_fraction == 1 and a.surface_evidence.sample_count == 0


@pytest.mark.parametrize("count", [0, 1, 10, 50, 100, 128])
def test_many_entities_all_retained_and_provider_independent(geometry, count):
    s = scene(geometry, count=count)
    b = replace(s, provenance=ComponentProvenance("alternative-world", "world_model"))
    a1, a2 = analyzer().analyze(s), analyzer().analyze(b)
    assert a1.entity_relations == a2.entity_relations and len(a2.entity_relations) == count


def test_missing_image_and_incompatible_schema(geometry):
    s = replace(scene(geometry), image_geometry=None)
    a = analyzer().analyze(s)
    assert (
        a.corridor.quality == "UNAVAILABLE" and a.entity_relations[0].relation == Relation.UNKNOWN
    )
    with pytest.raises(ValueError, match="schema"):
        analyzer().analyze(replace(s, schema_version=2))


def test_clip_projection_out_of_fov_and_unknown_visible_fraction(spatial):
    s = scene(spatial, metric=True)
    a = analyzer(spatial, near_half_width_m=4.0, far_half_width_m=4.0).analyze(s)
    assert a.corridor.image_polygon
    assert all(0 <= x <= 8 and 0 <= y <= 6 for x, y in a.corridor.image_polygon)
    assert a.corridor.observed_fraction is None
    assert clip_rect(((20.0, 20.0), (21.0, 20.0), (21.0, 21.0)), (0.0, 0.0, 8.0, 6.0)) == ()


def test_stale_entity_unknown_and_outside_preserved(geometry):
    s = scene(geometry)
    old = replace(s.entities[0], observation_age_ns=1_000_000_000)
    assert (
        analyzer().analyze(replace(s, entities=(old,))).entity_relations[0].relation
        == Relation.UNKNOWN
    )
    outside = replace(s.entities[0], image_geometry=Box(0, 1, 1, 4))
    a = analyzer().analyze(replace(s, entities=(outside,)))
    assert a.entity_relations[0].relation == Relation.OUTSIDE


def test_pipeline_recording_and_replaceable_analyzer(make_pipeline, geometry):
    class Alternative:
        def analyze(self, state):
            return analyzer().analyze(state)

    p, recorder = make_pipeline(
        {"world_model": {}, "corridor": {}, "record_session": True},
        motion_geometry=geometry,
        corridor_analyzer=Alternative(),
    )
    result = p.run(SyntheticSource([0, 10, 20]))
    assert result["termination_reason"] == "END_OF_STREAM"
    assert result["summary"]["corridor_analyses_published"] == 3
    frames = [r for r in records(recorder) if r["type"] == "frame_result"]
    assert len(frames) == 3 and all(r["schema_version"] == 7 for r in frames)
    assert all(
        r["corridor_analysis"]["state_timestamp"] == r["identity"]["observation_ns"] for r in frames
    )


@pytest.mark.parametrize(
    "case", ["relative", "point_quality", "negative_z", "stale_depth", "future_track"]
)
def test_metric_entity_gates_never_publish_unsupported_meters(spatial, case):
    from perception_lab.depth import DepthKind

    s = scene(spatial, metric=True)
    e = s.entities[0]
    if case == "relative":
        w = model(spatial)
        ts = tracks()
        w.ingest_tracks(ts, 0)
        w.ingest_depth(track_depth(ts, depth(spatial, relative=True))[0], 0)
        e = w.snapshot(0).entities[0]
        assert e.depth.representation.kind == DepthKind.RELATIVE
    elif case == "point_quality":
        e = replace(e, position_camera=replace(e.position_camera, calibration_quality="UNKNOWN"))
    elif case == "negative_z":
        e = replace(e, position_camera=replace(e.position_camera, position_meters=(0.0, 0.0, -1.0)))
    elif case == "stale_depth":
        e = replace(e, depth_evidence=replace(e.depth_evidence, status=EvidenceStatus.STALE))
    else:
        e = replace(e, track_evidence=replace(e.track_evidence, identity=identity(1)))
    relation = analyzer(spatial).analyze(replace(s, entities=(e,))).entity_relations[0]
    assert relation.forward_distance_m is None and relation.lateral_offset_m is None


def test_old_semantic_mask_is_not_aligned_after_a_turn(geometry):
    s = scene(geometry, count=0)
    surface = replace(
        s.surface_state,
        evidence=replace(evidence(), age_ns=1),
        camera_image_id=geometry.c.image_frame_id,
        dimensions=(8, 6),
        samples=((4.0, 5.0, 6),),
    )
    s = replace(
        s,
        state_timestamp=1,
        image_geometry=replace(s.image_geometry, evidence=evidence(1)),
        surface_state=surface,
    )
    a = analyzer().analyze(s)
    assert a.surface_evidence.unknown_fraction == 1
    assert a.surface_evidence.sample_count == 0


def test_exact_projection_and_expansion(spatial):
    s = scene(spatial, metric=True)
    c = CorridorConfig(near_m=1.0, far_m=5.0, near_half_width_m=1.0, far_half_width_m=1.0)
    core = spatial.corridor(s.ground_plane, None, c)
    assert np.asarray(core.project()) == pytest.approx(
        np.asarray(((-4.0, 11.0), (12.0, 11.0), (5.6, 4.6), (2.4, 4.6)))
    )
    a = analyzer(spatial, expansion_m=0.2).analyze(s)
    assert a.corridor.near_half_width_m == pytest.approx(0.65)


def test_unknown_category_never_assumes_ground_footprint(spatial):
    s = scene(spatial, metric=True)
    e = replace(s.entities[0], category=ObjectClass.UNKNOWN)
    relation = analyzer(spatial).analyze(replace(s, entities=(e,))).entity_relations[0]
    assert relation.coordinate_basis == "IMAGE_SPACE_RELATION"
    assert relation.lateral_offset_m is None
    assert relation.representative_source == "IMAGE_BBOX_BOTTOM_CENTER"


@pytest.mark.parametrize("normal", [(0.0, 0.0, 1.0), (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)])
def test_degenerate_plane_falls_back(spatial, normal):
    s = scene(spatial, metric=True)
    s = replace(s, ground_plane=replace(s.ground_plane, normal=normal))
    assert analyzer(spatial).analyze(s).corridor.mode == CorridorMode.IMAGE


@pytest.mark.parametrize("vendor", ["provider-a", "provider-b"])
def test_tracker_depth_semantic_providers_share_analysis_contract(spatial, vendor):
    from test_semantics import sample

    from perception_lab.surfaces import SurfaceEvidenceExtractor

    w = model(spatial)
    p = ComponentProvenance(vendor, "tracker")
    ts = replace(tracks(), provenance=p)
    w.ingest_tracks(ts, 0)
    w.ingest_depth(track_depth(ts, depth(spatial, name=vendor))[0], 0)
    _, semantic = sample(spatial)
    semantic = replace(semantic, provenance=ComponentProvenance(vendor, "segmentation"))
    w.ingest_surface(SurfaceEvidenceExtractor().extract(semantic), 0)
    s = replace(
        w.snapshot(0), image_geometry=WorldImageGeometry(spatial.c.image_frame_id, 8, 6, evidence())
    )
    a = analyzer(spatial).analyze(s)
    assert a.entity_relations[0].sources[0].provenance[0].name == vendor
    assert a.surface_evidence.validation_status == "UNVERIFIED"
    assert a.surface_evidence.sample_count > 0


def test_overlay_preserves_pixels_and_rejects_wrong_time(geometry):
    s = scene(geometry)
    a = analyzer().analyze(s)
    pixels = np.zeros((480, 640, 3), np.uint8)
    output = draw_corridor(pixels, s, a)
    assert np.count_nonzero(pixels) == 0 and np.count_nonzero(output) > 0
    with pytest.raises(ValueError, match="mismatch"):
        draw_corridor(pixels, s, replace(a, state_timestamp=1))


@pytest.mark.parametrize(
    "fields",
    [
        {"near_m": 5.0, "far_m": 1.0},
        {"near_half_width_m": -1.0},
        {"far_m": float("inf")},
        {"schema_version": 2},
    ],
)
def test_configuration_rejects_invalid_research_values(fields):
    with pytest.raises(ValueError):
        CorridorConfig(**fields)
