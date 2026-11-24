from dataclasses import FrozenInstanceError, asdict, replace

import pytest
from test_corridor import evidence, scene
from test_world_model import depth, identity, model, tracks
from test_world_model import spatial as spatial_fixture

from perception_lab.corridor import HybridCorridorAnalyzer
from perception_lab.corridor_config import CorridorConfig
from perception_lab.detection import Box
from perception_lab.trajectory import AdaptiveKinematicPredictor
from perception_lab.trajectory_config import TrajectoryConfig
from perception_lab.trajectory_corridor import entry_fraction, relate
from perception_lab.trajectory_fit import linear_fit
from perception_lab.trajectory_types import TrajectoryDomain, TrajectoryPhysicalStatus
from perception_lab.world_types import EntityHistory, WorldImageGeometry

spatial = spatial_fixture


def metric_history(g, relative=False):
    from perception_lab.contracts import ComponentProvenance
    from perception_lab.depth_sampling import track_depth
    from perception_lab.depth_spatial import SuppliedDepthPose

    w = model(g)
    for t in (0, 200_000_000, 400_000_000):
        ts = tracks(t)
        w.ingest_tracks(ts, t)
        w.ingest_depth(track_depth(ts, depth(g, t, relative=relative))[0], t)
        w.ingest_pose(
            "test",
            SuppliedDepthPose(
                identity(t), "device", "local-world", (t / 1e9 * 5, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)
            ),
            ComponentProvenance("fixture", "pose"),
            t,
            "SYNTHETIC",
        )
    return w.snapshot(t)


def test_world_research_uses_guardian_and_exact_history(spatial):
    state = metric_history(spatial)
    output = AdaptiveKinematicPredictor(TrajectoryConfig(), spatial).predict(state)
    trajectory = next(
        t for t in output.trajectories if t.coordinate_space == TrajectoryDomain.WORLD
    )
    assert trajectory.velocity == pytest.approx((5.0, 0.0, 0.0))
    assert trajectory.samples[-1].position[0] == pytest.approx(trajectory.origin[0] + 15.0)
    assert trajectory.samples[-1].position[1:] == pytest.approx(trajectory.origin[1:])
    assert trajectory.physical_status == TrajectoryPhysicalStatus.WORLD_RESEARCH_UNVALIDATED
    assert trajectory.velocity_status == "RESEARCH_METRIC_ESTIMATE"
    assert all(h.world_point.identity == h.identity for h in state.entities[0].history)


@pytest.mark.parametrize(
    "kind", ["relative", "no_pose", "bad_calibration", "stale_pose", "bad_source"]
)
def test_world_gates(spatial, kind):
    from perception_lab.world_types import EvidenceStatus

    state = metric_history(spatial, relative=kind == "relative")
    c = state.camera_state
    if kind == "no_pose":
        c = replace(c, pose=None)
    if kind == "bad_calibration":
        c = replace(c, calibration_id="wrong")
    if kind == "stale_pose":
        c = replace(c, pose_evidence=replace(c.pose_evidence, status=EvidenceStatus.STALE))
    if kind == "bad_source":
        e = state.entities[0]
        state = replace(
            state,
            entities=(
                replace(e, history=tuple(replace(h, position_sources=()) for h in e.history)),
            ),
        )
    output = AdaptiveKinematicPredictor(TrajectoryConfig(), spatial).predict(
        replace(state, camera_state=c)
    )
    assert not any(t.coordinate_space == TrajectoryDomain.WORLD for t in output.trajectories)


def test_bearing_uses_guardian_convention(spatial):
    state = metric_history(spatial)
    # Fixture center is (4,3); Guardian is authoritative, not a guessed pixel scale.
    h = state.entities[0].history[-1]
    expected = spatial.bearing_angles(4.0, 3.0, h.identity)
    assert h.bearing_radians == pytest.approx(expected)
    result = AdaptiveKinematicPredictor(TrajectoryConfig(), spatial).predict(state)
    bearing = next(t for t in result.trajectories if t.coordinate_space == TrajectoryDomain.BEARING)
    assert bearing.origin == pytest.approx(expected)
    assert bearing.units == "radians"


def test_calibration_change_drops_old_metric_and_bearing_history(spatial):
    state = metric_history(spatial)
    e = state.entities[0]
    e = replace(e, history=tuple(replace(h, calibration_id="old") for h in e.history))
    result = AdaptiveKinematicPredictor(TrajectoryConfig(), spatial).predict(
        replace(state, entities=(e,))
    )
    assert all(t.coordinate_space == TrajectoryDomain.IMAGE for t in result.trajectories)


def test_unknown_clock_cannot_produce_a_trajectory(geometry):
    from perception_lab.contracts import TimingProvenance

    state = moving(geometry)
    e = state.entities[0]
    e = replace(
        e,
        track_evidence=replace(
            e.track_evidence,
            identity=replace(e.track_evidence.identity, timing=TimingProvenance.UNKNOWN),
        ),
    )
    assert not predictor().predict(replace(state, entities=(e,))).trajectories


def test_newest_outlier_not_used_as_prediction_origin(geometry):
    state = moving(geometry, tuple(i * 100_000_000 for i in range(9)))
    e = state.entities[0]
    h = replace(e.history[-1], box=Box(1000.0, 1.0, 1004.0, 5.0))
    e = replace(e, history=(*e.history[:-1], h))
    trajectory = predictor().predict(replace(state, entities=(e,))).trajectories[0]
    assert trajectory.origin == pytest.approx((20.0, 5.0))
    assert trajectory.quality == "UNRELIABLE" and trajectory.rejected_observations == 1
    assert h.identity not in trajectory.source_observations


def test_json_horizons_are_supported():
    assert TrajectoryConfig.model_validate(
        {"horizons_ns": [250_000_000, 1_000_000_000]}
    ).horizons_ns == (250_000_000, 1_000_000_000)


def test_retrospective_evaluation_is_causal_and_identity_bound(geometry, monkeypatch):
    from pathlib import Path

    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    from trajectory_benchmark import MeasuredTrajectory

    measured = MeasuredTrajectory(TrajectoryConfig(), evaluate=True)
    state = moving(geometry, speed=0.0)
    result = measured.predict(state)
    frozen = asdict(result)
    assert measured.errors == {} and measured.pending
    future = state.state_timestamp + 250_000_000
    e = replace(state.entities[0], latest_observed_ns=future, state_timestamp=future)
    # Wrong identity is not accepted as retrospective truth.
    wrong = replace(e, entity_id=replace(e.entity_id, serial=999))
    measured.score(replace(state, state_timestamp=future, entities=(wrong,)))
    assert measured.errors == {}
    measured.score(replace(state, state_timestamp=future, entities=(e,)))
    assert measured.errors["ADAPTIVE:250000000"]["count"] == 1
    assert measured.errors["ADAPTIVE:250000000"]["sum_error_pixels"] == 0.0
    assert asdict(result) == frozen
    assert measured.overflow == 0


def test_residual_is_separate_stabilized_hypothesis(geometry):
    from perception_lab.flow import FramePair
    from perception_lab.motion import TrackImageMotionObservation
    from perception_lab.world_types import EvidenceStatus

    state = moving(geometry)
    e = state.entities[0]
    pair = FramePair(
        "test", identity(250_000_000), identity(400_000_000), "hash", "camera-image", 100, 100
    )
    motion = TrackImageMotionObservation(
        e.source_track_id, pair, (1.0, 0.0), (6.0, 0.0), (0.1, 0.1), 5, 1.0, "ROTATION_ONLY"
    )
    e = replace(
        e,
        image_motion=motion,
        motion_evidence=replace(e.motion_evidence, status=EvidenceStatus.DEGRADED),
    )
    state = replace(
        state,
        entities=(e,),
        camera_state=replace(
            state.camera_state, calibration_id="hash", calibration_quality="VALID"
        ),
    )
    corridor = HybridCorridorAnalyzer(CorridorConfig()).analyze(state)
    output = predictor().predict(state, corridor)
    residual = output.trajectories[-1]
    assert residual.model == "RESIDUAL_RATE_RESEARCH" and residual.velocity == (6.0, 0.0)
    assert output.corridor_relations[-1].current_relation == "UNKNOWN"
    assert output.preferred_trajectory_ids == (output.trajectories[0].trajectory_id,)


def test_pipeline_recording_schema_and_overlay(make_pipeline, geometry):
    import numpy as np
    from conftest import records

    from perception_lab.sources import SyntheticSource
    from perception_lab.trajectory_overlay import draw_trajectories

    p, recorder = make_pipeline(
        {"world_model": {}, "corridor": {}, "trajectory": {}, "record_session": True}
    )
    manifest = p.run(SyntheticSource(iter([0, 33_333_333])))
    assert manifest["schema_version"] == 8
    assert manifest["summary"]["trajectory_sets_published"] == 2
    frames = [x for x in records(recorder) if x["type"] == "frame_result"]
    assert all(
        x["schema_version"] == 8 and x["trajectory_set"]["schema_version"] == 1 for x in frames
    )
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    output = draw_trajectories(image, predictor().predict(moving(geometry)))
    assert not np.shares_memory(image, output) and not image.any() and output.any()


def moving(geometry, times=(0, 100_000_000, 250_000_000, 400_000_000), speed=20.0):
    s = scene(geometry)
    e = s.entities[0]
    history = tuple(
        EntityHistory(
            identity(t),
            Box(2 + speed * t / 1e9, 1, 6 + speed * t / 1e9, 5),
            e.category,
            "OBSERVED",
            0.8,
        )
        for t in times
    )
    now = times[-1]
    e = replace(
        e,
        history=history,
        state_timestamp=now,
        latest_observed_ns=now,
        image_geometry=history[-1].box,
        track_evidence=replace(e.track_evidence, identity=identity(now)),
    )
    return replace(
        s,
        state_timestamp=now,
        entities=(e,),
        image_geometry=WorldImageGeometry("camera-image", 100, 100, evidence(now)),
    )


def predictor(**kwargs):
    return AdaptiveKinematicPredictor(TrajectoryConfig(**kwargs))


def test_linear_irregular_dt_and_units(geometry):
    s = moving(geometry)
    before = asdict(s)
    result = predictor().predict(s)
    t = result.trajectories[0]
    assert t.model == "CV_WINDOW"
    assert t.velocity == pytest.approx((20, 0))
    assert t.samples[0].position == pytest.approx((17, 5))
    assert t.samples[-1].position == pytest.approx((72, 5))
    assert t.units == "pixels" and t.physical_status == TrajectoryPhysicalStatus.IMAGE_ONLY
    assert asdict(s) == before
    assert predictor().predict(s) == result
    assert all(
        a.envelope_radius < b.envelope_radius
        for a, b in zip(t.samples, t.samples[1:], strict=False)
    )
    assert all(s.timestamp_ns == t.prediction_start_timestamp + s.horizon_ns for s in t.samples)
    with pytest.raises(FrozenInstanceError):
        t.model = "other"


@pytest.mark.parametrize("model", ["ADAPTIVE", "CONSTANT_POSITION", "CV_LAST_TWO", "CV_WINDOW"])
def test_swap_and_single_observation_fallback(geometry, model):
    t = predictor(model=model).predict(moving(geometry, (0,))).trajectories[0]
    assert t.model == "CONSTANT_POSITION"
    assert all(s.position == (4, 5) for s in t.samples)
    assert "INSUFFICIENT_HISTORY" in t.reasons


def test_stationary(geometry):
    t = predictor().predict(moving(geometry, speed=0)).trajectories[0]
    assert t.model == "CONSTANT_POSITION"
    assert t.velocity == (0, 0)


def test_outlier_rejection():
    times = tuple(i / 10 for i in range(9))
    points = tuple((3 + 20 * t + (500 if i == 4 else 0), 5.0) for i, t in enumerate(times))
    fit = linear_fit(times, points, 2, 4)
    assert 4 not in fit.kept
    assert fit.velocity == pytest.approx((20, 0))
    assert fit.position == pytest.approx((19, 5))


def test_window_better_than_noisy_last_two():
    times = tuple(i / 10 for i in range(10))
    points = tuple((10 * t + (0.8 if i % 2 else -0.8), 0.0) for i, t in enumerate(times))
    robust = linear_fit(times, points, 2, 4)
    two = linear_fit(times, points, 2, 4, True)
    assert abs(robust.position[0] + robust.velocity[0] - 19) < abs(
        two.position[0] + two.velocity[0] - 19
    )


@pytest.mark.parametrize("last_two", [False, True])
def test_extreme_finite_inputs_cannot_publish_nonfinite_fit(last_two):
    with pytest.raises(ValueError, match="Non-finite fit"):
        linear_fit((0.0, 0.1, 0.2), ((-1e308, 0.0), (0.0, 0.0), (1e308, 0.0)), 2.0, 4.0, last_two)


@pytest.mark.parametrize("kind", ["future", "reverse", "source", "session"])
def test_bad_temporal_inputs_rejected(geometry, kind):
    s = moving(geometry)
    e = s.entities[0]
    h = e.history
    if kind == "future":
        h = (*h[:-1], replace(h[-1], identity=identity(s.state_timestamp + 1)))
    elif kind == "reverse":
        h = tuple(reversed(h))
    elif kind == "source":
        h = (*h[:-1], replace(h[-1], identity=replace(h[-1].identity, source_id="other")))
    else:
        e = replace(e, entity_id=replace(e.entity_id, session_id="other"))
    with pytest.raises(ValueError):
        predictor().predict(replace(s, entities=(replace(e, history=h),)))


def test_predicted_samples_do_not_feed_fit(geometry):
    s = moving(geometry)
    e = s.entities[0]
    h = replace(e.history[1], observation_status="PREDICTED", box=Box(1000, 1, 1004, 5))
    t = (
        predictor()
        .predict(replace(s, entities=(replace(e, history=(e.history[0], h, *e.history[2:])),)))
        .trajectories[0]
    )
    assert t.velocity == pytest.approx((20, 0))
    assert h.identity not in t.source_observations


def test_gap_resets_and_stale_unavailable(geometry):
    s = moving(geometry, (0, 100_000_000, 1_000_000_000))
    t = predictor().predict(s).trajectories[0]
    assert t.source_observation_count == 1 and t.model == "CONSTANT_POSITION"
    assert not predictor().predict(replace(s, state_timestamp=2_000_000_000)).trajectories


@pytest.mark.parametrize(
    "a,b,expected",
    [((3, 1), (-1, 1), 0.25), ((3, 1), (3, 5), None), ((1, 1), (4, 1), 0.0), ((3, 3), (2, 2), 1.0)],
)
def test_analytic_corridor_entry(a, b, expected):
    polygon = ((0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0))
    result = entry_fraction(a, b, polygon)
    assert result == pytest.approx(expected) if expected is not None else result is None
    assert entry_fraction(a, b, tuple(reversed(polygon))) == result


def test_crossing_between_horizons(geometry):
    s = moving(geometry, speed=-20)
    t = predictor().predict(s).trajectories[0]
    t = replace(
        t,
        origin=(3.0, 1.0),
        samples=tuple(replace(x, position=(3 - 4 * x.horizon_ns / 1e9, 1.0)) for x in t.samples),
    )
    a = HybridCorridorAnalyzer(CorridorConfig()).analyze(s)
    a = replace(
        a,
        corridor=replace(
            a.corridor, image_polygon=((0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0))
        ),
    )
    r = relate(t, a)
    assert r.predicted_corridor_entry_time_ns == 250_000_000
    assert r.current_relation == "PREDICTED_OUTSIDE"
    assert r.future_relations[-1][1] == "PREDICTED_OUTSIDE"


def test_alternate_predictor_path_is_not_assumed_straight(geometry):
    state = moving(geometry)
    trajectory = predictor().predict(state).trajectories[0]
    trajectory = replace(
        trajectory,
        model="ALTERNATE_PIECEWISE_FIXTURE",
        origin=(3.0, 1.0),
        samples=tuple(
            replace(s, position=(1.0, 1.0) if i == 0 else (3.0, 1.0))
            for i, s in enumerate(trajectory.samples)
        ),
    )
    corridor = HybridCorridorAnalyzer(CorridorConfig()).analyze(state)
    corridor = replace(
        corridor,
        corridor=replace(
            corridor.corridor, image_polygon=((0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0))
        ),
    )
    assert relate(trajectory, corridor).predicted_corridor_entry_time_ns == 125_000_000


@pytest.mark.parametrize(
    "kwargs",
    [
        {"horizons_ns": (0,)},
        {"horizons_ns": (3_000_000_001,)},
        {"horizons_ns": (2, 1)},
        {"horizons_ns": (1, 1)},
        {"history_count": 2},
        {"pixel_floor": float("nan")},
    ],
)
def test_bad_configuration(kwargs):
    with pytest.raises(ValueError):
        TrajectoryConfig(**kwargs)


def test_bearing_partial_representation(geometry):
    s = moving(geometry)
    e = s.entities[0]
    e = replace(
        e,
        history=tuple(
            replace(
                h, bearing_radians=(h.identity.observation_ns / 1e9, 0.0), calibration_id="test"
            )
            for h in e.history
        ),
    )
    s = replace(
        s,
        entities=(e,),
        camera_state=replace(s.camera_state, calibration_quality="VALID", calibration_id="test"),
    )
    outputs = predictor().predict(s).trajectories
    assert [t.coordinate_space for t in outputs] == [
        TrajectoryDomain.IMAGE,
        TrajectoryDomain.BEARING,
    ]
    assert outputs[1].units == "radians"
    assert outputs[1].velocity == pytest.approx((1, 0))
    assert outputs[1].physical_status == TrajectoryPhysicalStatus.CAMERA_RELATIVE


@pytest.mark.parametrize("count", [1, 10, 50, 100, 128, 512])
def test_bounded_many_entity_and_provider_swaps(geometry, count):
    s = moving(geometry)
    e = s.entities[0]
    entities = tuple(
        replace(
            e,
            entity_id=replace(e.entity_id, serial=i + 1),
            source_track_id=replace(e.source_track_id, serial=i + 1),
        )
        for i in range(count)
    )
    s = replace(s, entities=entities, provenance=replace(s.provenance, name="alternate-world"))
    result = predictor().predict(s)
    assert len(result.trajectories) == count
    assert len(set(result.preferred_trajectory_ids)) == count
