from dataclasses import FrozenInstanceError, asdict, replace

import pytest
from test_trajectory import metric_history, moving, predictor
from test_world_model import spatial as spatial_fixture

from perception_lab.corridor import HybridCorridorAnalyzer
from perception_lab.corridor_config import CorridorConfig
from perception_lab.corridor_types import CorridorMode
from perception_lab.interaction import TrajectoryCorridorInteractionAnalyzer
from perception_lab.interaction_config import InteractionConfig
from perception_lab.interaction_geometry import segment, validate_polygon
from perception_lab.interaction_types import InteractionLevel
from perception_lab.trajectory import AdaptiveKinematicPredictor
from perception_lab.trajectory_config import TrajectoryConfig
from perception_lab.trajectory_types import TrajectoryDomain

spatial = spatial_fixture
SQUARE = ((0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0))


def image_case(g, origin=(-1.0, 1.0), velocity=(2.0, 0.0), radius=0.0):
    state = moving(g)
    corridor = HybridCorridorAnalyzer(CorridorConfig()).analyze(state)
    corridor = replace(corridor, corridor=replace(corridor.corridor, image_polygon=SQUARE))
    ts = predictor().predict(state)
    t = ts.trajectories[0]
    t = replace(
        t,
        origin=origin,
        velocity=velocity,
        samples=tuple(
            replace(
                s,
                position=tuple(
                    p + v * s.horizon_ns / 1e9 for p, v in zip(origin, velocity, strict=True)
                ),
                envelope_radius=radius,
            )
            for s in t.samples
        ),
    )
    return state, corridor, replace(ts, trajectories=(t,))


def analyze(data, **options):
    return (
        TrajectoryCorridorInteractionAnalyzer(InteractionConfig(**options))
        .analyze(*data)
        .entity_interactions[0]
    )


def test_entry_exit_and_minimum_are_not_ttc(geometry):
    data = image_case(geometry)
    r = analyze(data)
    assert r.predicted_corridor_entry_time_ns == 500_000_000
    assert r.predicted_corridor_exit_time_ns == 1_500_000_000
    assert r.intersection_intervals_ns == ((500_000_000, 1_500_000_000),)
    assert r.closest_corridor_approach.distance == 0
    assert r.closest_corridor_approach.horizon_ns == 500_000_000
    assert r.interaction_type == "CROSS_CORRIDOR"
    assert r.crossing_direction == "LEFT_TO_RIGHT"
    assert r.ttc.seconds is None and r.cpa.time_seconds is None
    assert r.physical_validity == InteractionLevel.IMAGE
    assert r.earliest_possible_entry_ns is None and r.latest_possible_entry_ns is None


@pytest.mark.parametrize(
    "origin,velocity,kind,entry,exit_ns",
    [
        ((1.0, 1.0), (0.0, 0.0), "REMAIN_INSIDE", 0, None),
        ((1.0, 1.0), (2.0, 0.0), "PREDICTED_EXIT", 0, 500_000_000),
        ((3.0, 1.0), (-2.0, 0.0), "CROSS_CORRIDOR", 500_000_000, 1_500_000_000),
        ((-1.0, 3.0), (2.0, 0.0), "PASS_NEAR", None, None),
        ((-1.0, 2.0), (2.0, 0.0), "CROSS_CORRIDOR", 500_000_000, 1_500_000_000),
    ],
)
def test_static_parallel_grazing_and_reverse(geometry, origin, velocity, kind, entry, exit_ns):
    r = analyze(image_case(geometry, origin, velocity))
    assert (
        r.interaction_type,
        r.predicted_corridor_entry_time_ns,
        r.predicted_corridor_exit_time_ns,
    ) == (kind, entry, exit_ns)
    if origin == (3.0, 1.0):
        assert r.crossing_direction == "RIGHT_TO_LEFT"


@pytest.mark.parametrize(
    "radius,expected", [(0.5, "NO_INTERSECTION_WITHIN_ENVELOPE"), (1.1, "POSSIBLE_INTERSECTION")]
)
def test_envelope_miss_vs_possible(geometry, radius, expected):
    r = analyze(image_case(geometry, (-1.0, 3.0), (2.0, 0.0), radius))
    assert r.envelope_interaction == expected
    assert r.predicted_corridor_entry_time_ns is None
    assert r.closest_corridor_approach.distance == 1


def test_piecewise_path_not_chord_and_horizon_limit(geometry):
    state, corridor, ts = image_case(geometry, (-1.0, 1.0))
    t = ts.trajectories[0]
    t = replace(
        t,
        samples=tuple(
            replace(s, position=(1.0, 1.0) if i == 0 else (-1.0, 1.0))
            for i, s in enumerate(t.samples)
        ),
    )
    r = analyze((state, corridor, replace(ts, trajectories=(t,))), horizon_ns=500_000_000)
    assert r.predicted_corridor_entry_time_ns == 125_000_000
    assert r.predicted_corridor_exit_time_ns == 375_000_000
    assert r.horizon_ns == 500_000_000
    assert len(r.samples) == 2


@pytest.mark.parametrize(
    "kind",
    [
        "session",
        "time",
        "units",
        "frame_clock",
        "future",
        "nan",
        "horizon",
        "duplicates",
        "unknown_entity",
    ],
)
def test_invalid_input_rejected(geometry, kind):
    state, c, ts = image_case(geometry)
    t = ts.trajectories[0]
    if kind == "session":
        c = replace(c, session_id="other")
    elif kind == "time":
        ts = replace(ts, state_timestamp=ts.state_timestamp + 1)
    elif kind == "units":
        t = replace(t, units="meters")
    elif kind == "frame_clock":
        t = replace(t, source_observations=(replace(t.source_observations[0], source_id="other"),))
    elif kind == "future":
        t = replace(
            t,
            source_observations=(
                replace(t.source_observations[0], observation_ns=state.state_timestamp + 1),
            ),
        )
    elif kind == "nan":
        t = replace(t, origin=(float("nan"), 1.0))
    elif kind == "horizon":
        t = replace(t, samples=(replace(t.samples[0], horizon_ns=0),))
    elif kind == "unknown_entity":
        t = replace(t, entity_id=replace(t.entity_id, serial=999))
    ts = replace(ts, trajectories=(t, t) if kind == "duplicates" else (t,))
    with pytest.raises(ValueError):
        analyze((state, c, ts))


def test_stale_and_predicted_quality(geometry):
    state, c, ts = image_case(geometry)
    e = state.entities[0]
    stale = replace(
        e, latest_observed_ns=state.state_timestamp - 600_000_000, observation_age_ns=600_000_000
    )
    r = analyze((replace(state, entities=(stale,)), c, ts))
    assert r.quality == "UNAVAILABLE" and r.envelope_interaction == "UNKNOWN"
    r = analyze((replace(state, entities=(replace(e, observation_status="PREDICTED"),)), c, ts))
    assert r.quality == "UNRELIABLE"


def test_deterministic_immutable_and_no_identity_history(geometry):
    data = image_case(geometry)
    engine = TrajectoryCorridorInteractionAnalyzer(InteractionConfig())
    a = engine.analyze(*data)
    assert a == engine.analyze(*data)
    with pytest.raises(FrozenInstanceError):
        a.state_timestamp = 1
    state, c, ts = data
    eid = replace(state.entities[0].entity_id, serial=800)
    state = replace(state, entities=(replace(state.entities[0], entity_id=eid),))
    ts = replace(ts, trajectories=(replace(ts.trajectories[0], entity_id=eid),))
    b = engine.analyze(state, c, ts)
    assert b.entity_interactions[0].entity_id == eid
    assert "risk_score" not in asdict(b.entity_interactions[0])


@pytest.mark.parametrize(
    "r,v,closing,ttc,cpa,distance",
    [
        ((0.0, 10.0, 0.0), (0.0, -2.0, 0.0), 2.0, 5.0, 5.0, 0.0),
        ((2.0, 10.0, 0.0), (0.0, -2.0, 0.0), 20 / 104**0.5, 5.2, 5.0, 2.0),
        ((0.0, 10.0, 0.0), (0.0, 2.0, 0.0), -2.0, None, -5.0, None),
        ((0.0, 10.0, 0.0), (2.0, 0.0, 0.0), 0.0, None, 0.0, 10.0),
        ((0.0, 10.0, 0.0), (0.0, 0.0, 0.0), 0.0, None, None, None),
        ((0.0, 0.0, 0.0), (0.0, -2.0, 0.0), None, None, 0.0, 0.0),
    ],
)
def test_authoritative_bridge_analytical_cases(geometry, r, v, closing, ttc, cpa, distance):
    result = geometry.relative_motion("world", r, v, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    for actual, expected in (
        (result.closing_speed_mps, closing),
        (result.ttc_seconds, ttc),
        (result.cpa_seconds, cpa),
        (result.cpa_distance_meters, distance),
    ):
        assert actual is None if expected is None else actual == pytest.approx(expected)


def metric_case(g, position=(0.0, 4.0, 0.0), velocity=(0.0, -2.0, 0.0)):
    state = metric_history(g)
    ts = AdaptiveKinematicPredictor(TrajectoryConfig(), g).predict(state)
    t = next(t for t in ts.trajectories if t.coordinate_space == TrajectoryDomain.WORLD)
    t = replace(
        t,
        origin=position,
        velocity=velocity,
        samples=tuple(
            replace(
                s,
                position=tuple(
                    p + v * s.horizon_ns / 1e9 for p, v in zip(position, velocity, strict=True)
                ),
            )
            for s in t.samples
        ),
    )
    c = HybridCorridorAnalyzer(CorridorConfig()).analyze(state)
    c = replace(
        c,
        corridor=replace(
            c.corridor,
            mode=CorridorMode.WORLD,
            zone=replace(
                c.corridor.zone,
                coordinate_frame=t.frame_id,
                polygon=((-1.0, 1.0, 0.0), (1.0, 1.0, 0.0), (1.0, 3.0, 0.0), (-1.0, 3.0, 0.0)),
            ),
            origin=(0.0, 0.0, 0.0),
            forward=(0.0, 1.0, 0.0),
            lateral=(1.0, 0.0, 0.0),
        ),
    )
    # Zero reference supplied through current pose; object estimate is synthetic.
    state = replace(
        state,
        camera_state=replace(
            state.camera_state,
            pose=replace(state.camera_state.pose, translation_meters=(0.0, 0.0, 0.0)),
        ),
    )
    return state, c, replace(ts, trajectories=(t,))


@pytest.mark.parametrize(
    "position,velocity,ttc_status,cpa_status",
    [
        ((0.0, 4.0, 0.0), (0.0, -2.0, 0.0), "COMPUTABLE_RESEARCH", "COMPUTABLE_RESEARCH"),
        ((2.0, 4.0, 0.0), (0.0, -2.0, 0.0), "COMPUTABLE_RESEARCH", "COMPUTABLE_RESEARCH"),
        (
            (0.0, 10.0, 0.0),
            (0.0, -2.0, 0.0),
            "OUTSIDE_PREDICTION_HORIZON",
            "OUTSIDE_PREDICTION_HORIZON",
        ),
        ((0.0, 4.0, 0.0), (0.0, 2.0, 0.0), "NON_CLOSING", "PAST_CLOSEST_APPROACH"),
        ((0.0, 2.0, 0.0), (0.0, 0.0, 0.0), "NON_CLOSING", "ZERO_RELATIVE_VELOCITY"),
    ],
)
def test_research_metric_and_statuses(spatial, position, velocity, ttc_status, cpa_status):
    data = metric_case(spatial, position, velocity)
    engine = TrajectoryCorridorInteractionAnalyzer(
        InteractionConfig(research_metric=True, static_user_reference=True), spatial
    )
    r = engine.analyze(*data).entity_interactions[0]
    assert r.ttc.status == ttc_status and r.cpa.status == cpa_status
    assert r.ttc.physical_validation == r.cpa.physical_validation == "NO"
    assert "STATIC_USER_ASSUMPTION" in r.ttc.assumptions
    assert r.physical_validity == InteractionLevel.WORLD
    if position == (0.0, 4.0, 0.0) and velocity == (0.0, -2.0, 0.0):
        assert r.ttc.seconds == 2 and r.cpa.distance_meters == 0
        assert r.predicted_corridor_entry_time_ns == 500_000_000
    if position == (2.0, 4.0, 0.0):
        assert r.cpa.distance_meters == 2
        assert "FINITE_TTC_BUT_NO_CORRIDOR_INTERSECTION" in r.diagnostics


def test_relative_depth_and_missing_reference_cannot_produce_ttc(spatial):
    state, c, ts = metric_case(spatial)
    engine = TrajectoryCorridorInteractionAnalyzer(InteractionConfig(research_metric=True), spatial)
    assert (
        engine.analyze(state, c, ts).entity_interactions[0].ttc.status
        == "USER_VELOCITY_UNAVAILABLE"
    )
    from perception_lab.depth import DepthAxis, DepthKind

    e = state.entities[0]
    e = replace(
        e,
        depth=replace(
            e.depth,
            representation=replace(
                e.depth.representation, kind=DepthKind.RELATIVE, axis=DepthAxis.NONE
            ),
        ),
    )
    r = engine.analyze(replace(state, entities=(e,)), c, ts).entity_interactions[0]
    assert r.ttc.seconds is None and r.cpa.time_seconds is None
    assert r.ttc.status == "INSUFFICIENT_POSITION"


@pytest.mark.parametrize("model", ["CONSTANT_POSITION", "CV_LAST_TWO", "CV_WINDOW", "ADAPTIVE"])
def test_predictor_swaps(geometry, model):
    s = moving(geometry)
    c = HybridCorridorAnalyzer(CorridorConfig()).analyze(s)
    ts = AdaptiveKinematicPredictor(TrajectoryConfig(model=model)).predict(s, c)
    r = TrajectoryCorridorInteractionAnalyzer(InteractionConfig()).analyze(s, c, ts)
    assert r.entity_interactions and r.state_timestamp == s.state_timestamp


@pytest.mark.parametrize(
    "p",
    [
        ((0.0, 0.0),) * 3,
        ((0.0, 0.0), (2.0, 2.0), (0.0, 2.0), (2.0, 0.0)),
        ((0.0, 0.0), (2.0, 0.0), (1.0, 0.5), (2.0, 2.0), (0.0, 2.0)),
    ],
)
def test_invalid_polygons(p):
    with pytest.raises(ValueError):
        validate_polygon(p)


def test_segment_distance_and_clockwise_polygon():
    validate_polygon(SQUARE[::-1])
    interval, distance, time = segment((-1.0, 3.0), (3.0, 3.0), SQUARE[::-1])
    assert interval is None and distance == 1 and time == 0.25


def test_pipeline_recording_overlay_and_analyzer_swap(make_pipeline, geometry):
    import numpy as np
    from conftest import records

    from perception_lab.interaction_overlay import draw_interactions
    from perception_lab.sources import SyntheticSource

    class Replacement:
        def __init__(self):
            self.calls = 0
            self.delegate = TrajectoryCorridorInteractionAnalyzer(InteractionConfig())

        def analyze(self, state, corridor, trajectories, reference=None):
            self.calls += 1
            return self.delegate.analyze(state, corridor, trajectories, reference)

    alternate = Replacement()
    p, recorder = make_pipeline(
        {
            "world_model": {},
            "corridor": {},
            "trajectory": {},
            "interaction": {},
            "record_session": True,
        },
        interaction_analyzer=alternate,
    )
    manifest = p.run(SyntheticSource(iter([0, 33_333_333])))
    assert manifest["schema_version"] == 9 and alternate.calls == 2
    assert manifest["summary"]["interaction_analyses_published"] == 2
    frames = [x for x in records(recorder) if x["type"] == "frame_result"]
    assert len(frames) == 2
    assert all(
        x["schema_version"] == 9 and x["interaction_analysis"]["schema_version"] == 1
        for x in frames
    )
    image = np.zeros((200, 640, 3), dtype=np.uint8)
    result = TrajectoryCorridorInteractionAnalyzer(InteractionConfig()).analyze(
        *image_case(geometry)
    )
    output = draw_interactions(image, result)
    assert not np.shares_memory(output, image) and not image.any() and output.any()


@pytest.mark.parametrize(
    "options",
    [
        {"horizon_ns": 0},
        {"near_boundary_pixels": float("nan")},
        {"history_retention": 1},
        {"research_metric": "true"},
    ],
)
def test_strict_configuration(options):
    with pytest.raises(ValueError):
        InteractionConfig(**options)


def test_no_hidden_task_enablement(config):
    from perception_lab.config import LabConfig

    with pytest.raises(ValueError):
        LabConfig.model_validate({**config.model_dump(), "interaction": {}})


def test_unknown_envelope_and_wrong_image_frame(geometry):
    s, c, ts = image_case(geometry, (-1.0, 3.0), (2.0, 0.0), 2.0)
    t = replace(ts.trajectories[0], uncertainty_status="UNKNOWN")
    assert analyze((s, c, replace(ts, trajectories=(t,)))).envelope_interaction == "UNKNOWN"
    t = replace(t, frame_id="different-camera")
    r = analyze((s, c, replace(ts, trajectories=(t,))))
    assert r.envelope_interaction == "UNKNOWN" and r.closest_corridor_approach is None


def test_bearing_approach_is_not_range(geometry):
    from perception_lab.trajectory_types import TrajectoryPhysicalStatus

    s, c, ts = image_case(geometry)
    s = replace(s, camera_state=replace(s.camera_state, calibration_id="bearing-fixture"))
    c = replace(c, calibration_id="bearing-fixture")
    t = ts.trajectories[0]
    t = replace(
        t,
        coordinate_space=TrajectoryDomain.BEARING,
        physical_status=TrajectoryPhysicalStatus.CAMERA_RELATIVE,
        frame_id="bearing-fixture",
        units="radians",
        origin=(0.6, 0.0),
        velocity=(-0.1, 0.0),
        samples=tuple(
            replace(x, position=(0.6 - 0.1 * x.horizon_ns / 1e9, 0.0)) for x in t.samples
        ),
    )
    r = analyze((s, c, replace(ts, trajectories=(t,))))
    assert r.approach_evidence.state == "APPROACHING"
    assert r.approach_evidence.reference_type == "CAMERA_FORWARD_BEARING_NOT_RANGE"
    assert r.ttc.seconds is None and r.closest_corridor_approach is None


@pytest.mark.parametrize("kind", ["session", "time", "units", "frame"])
def test_reference_mismatch_rejected(spatial, kind):
    from perception_lab.interaction_types import ReferenceMotion

    s, c, ts = metric_case(spatial)
    r = ReferenceMotion(
        s.session_id,
        s.state_timestamp,
        ts.trajectories[0].frame_id,
        (0.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        "FUTURE_USER_TRAJECTORY",
        "UNVALIDATED",
        "DEGRADED",
        (),
    )
    r = replace(
        r,
        **{
            "session": {"session_id": "other"},
            "time": {"state_timestamp": 0},
            "units": {"units": "pixels"},
            "frame": {"frame_id": "wrong"},
        }[kind],
    )
    engine = TrajectoryCorridorInteractionAnalyzer(InteractionConfig(research_metric=True), spatial)
    with pytest.raises(ValueError):
        engine.analyze(s, c, ts, r)


def test_supplied_user_reference_delegates_relative_velocity(spatial):
    from perception_lab.interaction_types import ReferenceMotion

    s, c, ts = metric_case(spatial, position=(0.0, 4.0, 0.0), velocity=(0.0, 0.0, 0.0))
    r = ReferenceMotion(
        s.session_id,
        s.state_timestamp,
        ts.trajectories[0].frame_id,
        (0.0, 0.0, 0.0),
        (0.0, 2.0, 0.0),
        "FUTURE_USER_TRAJECTORY",
        "UNVALIDATED",
        "DEGRADED",
        (),
    )
    output = (
        TrajectoryCorridorInteractionAnalyzer(InteractionConfig(research_metric=True), spatial)
        .analyze(s, c, ts, r)
        .entity_interactions[0]
    )
    assert output.ttc.seconds == 2 and output.cpa.distance_meters == 0
    assert output.ttc.physical_validation == "NO"
    assert "STATIC_USER_ASSUMPTION" not in output.ttc.assumptions


@pytest.mark.parametrize("count", [1, 10, 50, 100, 128, 512])
def test_many_entity_replacement_world(geometry, count):
    s, c, ts = image_case(geometry)
    entities = tuple(
        replace(s.entities[0], entity_id=replace(s.entities[0].entity_id, serial=i + 1))
        for i in range(count)
    )
    s = replace(s, entities=entities)
    ts = replace(
        ts,
        trajectories=tuple(
            replace(
                ts.trajectories[0],
                entity_id=e.entity_id,
                trajectory_id=f"alternate:{e.entity_id.serial}",
            )
            for e in entities
        ),
    )
    result = TrajectoryCorridorInteractionAnalyzer(InteractionConfig()).analyze(s, c, ts)
    assert len(result.entity_interactions) == count
    assert all(
        r.predicted_corridor_entry_time_ns == 500_000_000 for r in result.entity_interactions
    )


def test_retrospective_freezes_predictions_and_censors_identity_loss(geometry, monkeypatch):
    from pathlib import Path

    from perception_lab.detection import Box

    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    from interaction_benchmark import MeasuredInteraction

    s, c, ts = image_case(geometry)
    e = replace(s.entities[0], image_geometry=Box(-2.0, -1.0, 0.0, 1.0))
    s = replace(s, entities=(e,))
    engine = MeasuredInteraction(InteractionConfig(), evaluate=True)
    frozen = engine.analyze(s, c, ts)
    assert engine.evaluated == 0 and len(engine.pending) == 1
    for i in range(1, 31):
        now = s.state_timestamp + i * 100_000_000
        x = -1 + i * 0.2
        future = replace(
            e,
            state_timestamp=now,
            latest_observed_ns=now,
            image_geometry=Box(x - 1, -1.0, x + 1, 1.0),
        )
        engine._score(replace(s, state_timestamp=now, entities=(future,)))
    assert engine.events["TP"] == 1 and engine.evaluated == 1 and engine.overflow == 0
    assert engine.report()["retrospective"]["entry_timing_mae_seconds"] == pytest.approx(0)
    assert frozen.entity_interactions[0].predicted_corridor_entry_time_ns == 500_000_000
    other = MeasuredInteraction(InteractionConfig(), evaluate=True)
    other.analyze(s, c, ts)
    other._score(replace(s, state_timestamp=s.state_timestamp + 3_000_000_000, entities=()))
    assert other.censored == 1 and other.evaluated == 0


@pytest.mark.parametrize(
    "position,velocity,ttc,cpa_distance,entry",
    [
        ((0.0, 4.0, 0.0), (0.0, -2.0, 0.0), 2.0, 0.0, 500_000_000),
        ((2.0, 4.0, 0.0), (0.0, -2.0, 0.0), 2.5, 2.0, None),
        ((-2.0, 2.0, 0.0), (2.0, 0.0, 0.0), 2.0, 2.0, 500_000_000),
        ((0.0, 2.0, 0.0), (0.0, 0.0, 0.0), None, None, 0),
    ],
)
def test_actual_task013_world_fit_to_interaction(
    spatial, position, velocity, ttc, cpa_distance, entry
):
    s, c, _ = metric_case(spatial, position, velocity)
    e = s.entities[0]
    histories = tuple(
        replace(
            h,
            world_point=replace(
                h.world_point,
                position_meters=tuple(
                    p + v * (h.identity.observation_ns - s.state_timestamp) / 1e9
                    for p, v in zip(position, velocity, strict=True)
                ),
            ),
        )
        for h in e.history
    )
    e = replace(e, history=histories, position_world=histories[-1].world_point)
    s = replace(s, entities=(e,))
    ts = AdaptiveKinematicPredictor(TrajectoryConfig(model="CV_WINDOW"), spatial).predict(s, c)
    t = next(t for t in ts.trajectories if t.coordinate_space == TrajectoryDomain.WORLD)
    assert t.origin == pytest.approx(position) and t.velocity == pytest.approx(velocity)
    result = TrajectoryCorridorInteractionAnalyzer(
        InteractionConfig(research_metric=True, static_user_reference=True), spatial
    ).analyze(s, c, ts)
    r = next(r for r in result.entity_interactions if r.trajectory_id == t.trajectory_id)
    assert r.ttc.seconds is None if ttc is None else r.ttc.seconds == pytest.approx(ttc)
    assert (
        r.cpa.distance_meters is None
        if cpa_distance is None
        else r.cpa.distance_meters == pytest.approx(cpa_distance)
    )
    assert r.predicted_corridor_entry_time_ns == entry
    assert r.ttc.physical_validation == r.cpa.physical_validation == "NO"


@pytest.mark.parametrize("kind", ["velocity", "calibration"])
def test_replacement_metric_evidence_cannot_bypass_validity(spatial, kind):
    s, c, ts = metric_case(spatial)
    if kind == "velocity":
        ts = replace(ts, trajectories=(replace(ts.trajectories[0], velocity_status="UNAVAILABLE"),))
    else:
        s = replace(s, camera_state=replace(s.camera_state, calibration_id="other"))
        c = replace(c, calibration_id="other")
    r = (
        TrajectoryCorridorInteractionAnalyzer(
            InteractionConfig(research_metric=True, static_user_reference=True), spatial
        )
        .analyze(s, c, ts)
        .entity_interactions[0]
    )
    assert r.ttc.seconds is None and r.cpa.time_seconds is None
