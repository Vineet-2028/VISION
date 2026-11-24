from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest
from test_interaction import image_case

from perception_lab.config import LabConfig
from perception_lab.corridor_types import Relation
from perception_lab.detection import ObjectClass
from perception_lab.interaction import TrajectoryCorridorInteractionAnalyzer
from perception_lab.interaction_config import InteractionConfig
from perception_lab.interaction_types import InteractionLevel
from perception_lab.risk import RuleBasedRiskEngine
from perception_lab.risk_config import RiskConfig
from perception_lab.risk_overlay import draw_risk
from perception_lab.risk_types import RiskLevel, RiskQuality, RiskTrend
from perception_lab.world_types import EvidenceStatus


def case(
    geometry,
    relation=Relation.OUTSIDE,
    kind="CROSS_CORRIDOR",
    entry=500_000_000,
    approach="APPROACHING",
    envelope="NOMINAL_INTERSECTION",
):
    """Policy fixture: upstream geometry is tested separately, values are explicit inputs."""
    state, corridor, paths = image_case(geometry)
    e = state.entities[0]
    e = replace(
        e,
        quality="GOOD",
        observation_status="OBSERVED",
        track_evidence=replace(e.track_evidence, age_ns=0, status=EvidenceStatus.FRESH),
    )
    state = replace(state, entities=(e,), scene_quality=replace(state.scene_quality, state="GOOD"))
    r = replace(
        corridor.entity_relations[0],
        relation=relation,
        quality="GOOD",
        coordinate_basis="IMAGE_SPACE_RELATION",
    )
    corridor = replace(
        corridor,
        entity_relations=(r,),
        quality="GOOD",
        corridor=replace(corridor.corridor, quality="GOOD"),
    )
    path = replace(paths.trajectories[0], quality="GOOD")
    paths = replace(paths, trajectories=(path,))
    analysis = TrajectoryCorridorInteractionAnalyzer(InteractionConfig()).analyze(
        state, corridor, paths
    )
    f = analysis.entity_interactions[0]
    f = replace(
        f,
        quality="GOOD",
        interaction_type=kind,
        predicted_corridor_entry_time_ns=entry,
        envelope_interaction=envelope,
        approach_evidence=replace(f.approach_evidence, state=approach),
    )
    return state, corridor, paths, replace(analysis, quality="GOOD", entity_interactions=(f,))


def assess(data, config=None):
    return RuleBasedRiskEngine(config or RiskConfig()).assess(*data).assessments[0]


@pytest.mark.parametrize(
    "relation,kind,entry,approach,envelope,expected",
    [
        (Relation.INSIDE, "REMAIN_INSIDE", 0, "STABLE", "NOMINAL_INTERSECTION", RiskLevel.HIGH),
        (
            Relation.OUTSIDE,
            "REMAIN_OUTSIDE",
            None,
            "STABLE",
            "NO_INTERSECTION_WITHIN_ENVELOPE",
            RiskLevel.LOW,
        ),
        (
            Relation.OUTSIDE,
            "CROSS_CORRIDOR",
            500_000_000,
            "APPROACHING",
            "NOMINAL_INTERSECTION",
            RiskLevel.HIGH,
        ),
        (
            Relation.OUTSIDE,
            "CROSS_CORRIDOR",
            2_000_000_000,
            "APPROACHING",
            "NOMINAL_INTERSECTION",
            RiskLevel.ELEVATED,
        ),
        (
            Relation.OUTSIDE,
            "REMAIN_OUTSIDE",
            None,
            "RECEDING",
            "NO_INTERSECTION_WITHIN_ENVELOPE",
            RiskLevel.LOW,
        ),
        (
            Relation.INSIDE,
            "PREDICTED_EXIT",
            0,
            "RECEDING",
            "NOMINAL_INTERSECTION",
            RiskLevel.ELEVATED,
        ),
        (
            Relation.OUTSIDE,
            "PASS_NEAR",
            None,
            "APPROACHING",
            "POSSIBLE_INTERSECTION",
            RiskLevel.ELEVATED,
        ),
        (Relation.UNKNOWN, "UNKNOWN", None, "UNKNOWN", "UNKNOWN", RiskLevel.UNDETERMINED),
    ],
)
def test_scenario_policy(geometry, relation, kind, entry, approach, envelope, expected):
    r = assess(case(geometry, relation, kind, entry, approach, envelope))
    assert r.risk_level == expected
    assert r.research_score is None and not r.physical_risk_validated
    assert "UPSTREAM_INTERACTION_LOW_RECALL" in r.reason_codes
    assert r.physical_validity != InteractionLevel.PHYSICAL
    assert r.evidence_quality == (
        RiskQuality.INSUFFICIENT if expected == RiskLevel.UNDETERMINED else RiskQuality.DEGRADED
    )


@pytest.mark.parametrize("category", [ObjectClass.PERSON, ObjectClass.BICYCLE, ObjectClass.CAR])
def test_class_does_not_determine_risk(geometry, category):
    data = case(geometry)
    s = replace(data[0], entities=(replace(data[0].entities[0], category=category),))
    assert assess((s, *data[1:])).risk_level == RiskLevel.HIGH


def test_static_obstacle_without_any_future_or_physical_evidence(geometry):
    s, c, _, _ = case(geometry, relation=Relation.INSIDE)
    r = assess((s, c, None, None))
    assert r.risk_level == RiskLevel.HIGH
    assert r.physical_validity == InteractionLevel.IMAGE
    assert "CURRENTLY_INSIDE_CORRIDOR" in r.reason_codes


@pytest.mark.parametrize("missing", ["all", "interaction", "trajectory", "corridor"])
def test_missing_evidence_never_low(geometry, missing):
    data = list(case(geometry))
    for index, name in enumerate(("world", "corridor", "trajectory", "interaction")):
        if index and missing in {name, "all"}:
            data[index] = None
    r = assess(data)
    assert r.risk_level == RiskLevel.UNDETERMINED


@pytest.mark.parametrize("field", ["predicted", "stale", "future", "bad_quality"])
def test_track_quality_gate(geometry, field):
    s, c, ts, ia = case(geometry, relation=Relation.INSIDE)
    e = s.entities[0]
    if field == "predicted":
        e = replace(e, observation_status="PREDICTED")
    elif field == "stale":
        e = replace(
            e, latest_observed_ns=s.state_timestamp - 600_000_000, observation_age_ns=600_000_000
        )
    elif field == "future":
        e = replace(e, latest_observed_ns=s.state_timestamp + 1)
    else:
        e = replace(e, quality="UNAVAILABLE")
    assert assess((replace(s, entities=(e,)), c, ts, ia)).risk_level == RiskLevel.UNDETERMINED


@pytest.mark.parametrize("source", ["corridor", "trajectory", "interaction"])
def test_stale_joins_fail_closed(geometry, source):
    data = list(case(geometry))
    index = {"corridor": 1, "trajectory": 2, "interaction": 3}[source]
    data[index] = replace(data[index], state_timestamp=data[0].state_timestamp - 1)
    assert assess(data).risk_level == RiskLevel.UNDETERMINED


def test_unvalidated_ttc_and_cpa_cannot_dominate(geometry):
    data = case(
        geometry, kind="REMAIN_OUTSIDE", entry=None, envelope="NO_INTERSECTION_WITHIN_ENVELOPE"
    )
    ia = data[3]
    f = ia.entity_interactions[0]
    for distance in (0.0, 100.0):
        changed = replace(
            f,
            ttc=replace(f.ttc, seconds=0.001),
            cpa=replace(f.cpa, time_seconds=0.001, distance_meters=distance),
        )
        r = assess((*data[:3], replace(ia, entity_interactions=(changed,))))
        assert r.risk_level == RiskLevel.LOW
        assert "TTC_CPA_DIAGNOSTIC_ONLY" in r.reason_codes


def test_no_physical_promotion_from_string(geometry):
    data = case(geometry)
    ia = data[3]
    f = replace(ia.entity_interactions[0], physical_validity=InteractionLevel.PHYSICAL)
    assert (
        assess((*data[:3], replace(ia, entity_interactions=(f,)))).risk_level
        == RiskLevel.UNDETERMINED
    )


def test_unreliable_trajectory_not_low(geometry):
    data = case(
        geometry, kind="REMAIN_OUTSIDE", entry=None, envelope="NO_INTERSECTION_WITHIN_ENVELOPE"
    )
    paths = replace(data[2], trajectories=(replace(data[2].trajectories[0], quality="UNRELIABLE"),))
    assert assess((*data[:2], paths, data[3])).risk_level == RiskLevel.UNDETERMINED


def advance(data, delta=100_000_000):
    s, c, ts, ia = data
    now = s.state_timestamp + delta
    e = s.entities[0]
    e = replace(
        e,
        state_timestamp=now,
        latest_observed_ns=now,
        track_evidence=replace(
            e.track_evidence, identity=replace(e.track_evidence.identity, observation_ns=now)
        ),
    )
    s = replace(s, state_timestamp=now, entities=(e,))
    c = replace(
        c,
        state_timestamp=now,
        corridor=replace(
            c.corridor,
            state_timestamp=now,
            heading_evidence=replace(
                c.corridor.heading_evidence,
                identity=replace(c.corridor.heading_evidence.identity, observation_ns=now),
            ),
        ),
        entity_relations=tuple(
            replace(r, state_timestamp=now, sources=(e.track_evidence,)) for r in c.entity_relations
        ),
    )
    ts = replace(
        ts,
        state_timestamp=now,
        trajectories=tuple(
            replace(t, source_state_timestamp=now, prediction_start_timestamp=now)
            for t in ts.trajectories
        ),
    )
    ia = replace(
        ia,
        state_timestamp=now,
        entity_interactions=tuple(replace(f, state_timestamp=now) for f in ia.entity_interactions),
    )
    return s, c, ts, ia


def test_trends_expiry_disappearance_and_clock(geometry):
    data = case(geometry, relation=Relation.INSIDE)
    engine = RuleBasedRiskEngine(RiskConfig())
    assert engine.assess(*data).assessments[0].trend == RiskTrend.UNKNOWN
    later = advance(data)
    assert engine.assess(*later).assessments[0].trend == RiskTrend.STABLE
    empty = replace(later[0], state_timestamp=later[0].state_timestamp + 1, entities=())
    output = engine.assess(empty, None, None, None)
    assert engine.history_size == 0 and output.assessments == ()
    assert "EMPTY_SET_NOT_SAFE" in output.diagnostics
    with pytest.raises(ValueError, match="backwards"):
        engine.assess(*data)
    engine.reset()
    engine.assess(*data)
    stale = replace(data[0], state_timestamp=data[0].state_timestamp + 2_000_000_000)
    r = engine.assess(stale, None, None, None).assessments[0]
    assert r.risk_level == RiskLevel.UNDETERMINED and r.trend == RiskTrend.UNKNOWN


def test_identity_switch_no_inheritance(geometry):
    data = case(geometry)
    engine = RuleBasedRiskEngine(RiskConfig())
    engine.assess(*data)
    later = advance(data)
    entity = later[0].entities[0]
    entity = replace(entity, entity_id=replace(entity.entity_id, serial=999))
    r = engine.assess(replace(later[0], entities=(entity,)), None, None, None).assessments[0]
    assert r.trend == RiskTrend.UNKNOWN and engine.history_size == 1


def test_immutable_deterministic_overlay(geometry):
    data = case(geometry)
    first = RuleBasedRiskEngine(RiskConfig()).assess(*data)
    assert first.provenance.component_type == "risk"
    assert first.provenance.configuration_hash == first.config_hash
    assert first == RuleBasedRiskEngine(RiskConfig()).assess(*data)
    with pytest.raises(FrozenInstanceError):
        first.state_timestamp = 0
    pixels = np.zeros((480, 640, 3), dtype=np.uint8)
    drawn = draw_risk(pixels, first)
    assert pixels.sum() == 0 and drawn.sum() > 0


@pytest.mark.parametrize(
    "options",
    [
        dict(max_entities=0),
        dict(urgent_entry_ns=-1),
        dict(unvalidated_ttc_policy="TRUST"),
        dict(engine="neural"),
    ],
)
def test_strict_config(options):
    with pytest.raises(ValueError):
        RiskConfig(**options)


def test_pipeline_requires_explicit_world(config):
    with pytest.raises(ValueError, match="Risk requires"):
        LabConfig.model_validate({**config.model_dump(), "risk": {}})


def test_ordering_crossing_over_parallel(geometry):
    parallel = assess(
        case(
            geometry, kind="REMAIN_OUTSIDE", entry=None, envelope="NO_INTERSECTION_WITHIN_ENVELOPE"
        )
    )
    crossing = assess(case(geometry))
    assert parallel.risk_level == RiskLevel.LOW and crossing.risk_level == RiskLevel.HIGH


def test_pipeline_recording_and_engine_swap(make_pipeline):
    from conftest import records

    from perception_lab.sources import SyntheticSource

    class Replacement:
        def __init__(self):
            self.delegate = RuleBasedRiskEngine(RiskConfig())
            self.calls = 0
            self.resets = 0

        def assess(self, *args):
            self.calls += 1
            return self.delegate.assess(*args)

        def reset(self):
            self.resets += 1
            self.delegate.reset()

    alternate = Replacement()
    pipeline, recorder = make_pipeline(
        {
            "world_model": {},
            "corridor": {},
            "trajectory": {},
            "interaction": {},
            "risk": {},
            "record_session": True,
        },
        risk_engine=alternate,
    )
    manifest = pipeline.run(SyntheticSource(iter([0, 33_333_333])))
    assert alternate.calls == 2 and alternate.resets == 1
    assert manifest["schema_version"] == 10
    assert manifest["summary"]["risk_assessment_sets_published"] == 2
    frames = [x for x in records(recorder) if x["type"] == "frame_result"]
    assert len(frames) == 2
    assert all(
        x["schema_version"] == 10
        and x["risk_assessment_set"]["schema_version"] == 1
        and "EMPTY_SET_NOT_SAFE" in x["risk_assessment_set"]["diagnostics"]
        for x in frames
    )


@pytest.mark.parametrize("source", ["track", "heading", "relation"])
def test_stale_source_cannot_support_occupancy(geometry, source):
    s, c, ts, ia = case(geometry, relation=Relation.INSIDE)
    if source == "track":
        e = s.entities[0]
        s = replace(
            s, entities=(replace(e, track_evidence=replace(e.track_evidence, age_ns=600_000_000)),)
        )
    elif source == "heading":
        c = replace(
            c,
            corridor=replace(
                c.corridor,
                heading_evidence=replace(c.corridor.heading_evidence, age_ns=600_000_000),
            ),
        )
    else:
        r = c.entity_relations[0]
        c = replace(
            c, entity_relations=(replace(r, sources=(replace(r.sources[0], age_ns=600_000_000),)),)
        )
    assert assess((s, c, ts, ia)).risk_level == RiskLevel.UNDETERMINED


def test_proxy_funnel_hook_uses_frozen_risk_decision():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
    from risk_benchmark import ProxyInteraction

    proxy = ProxyInteraction(InteractionConfig())
    proxy.on_evaluated({"risk": "UNDETERMINED", "sensitivity": []}, True, True)
    proxy.on_evaluated({"risk": "HIGH", "sensitivity": []}, True, True)
    assert proxy.risk_events == {"FN": 1, "TP": 1}
    assert proxy.conditional["proxy_relevant"] == 2
    assert proxy.conditional["risk_raised_given_interaction"] == 1


def test_unknown_alternative_prevents_low(geometry):
    s, c, ts, ia = case(
        geometry, kind="REMAIN_OUTSIDE", entry=None, envelope="NO_INTERSECTION_WITHIN_ENVELOPE"
    )
    alternate = replace(ts.trajectories[0], trajectory_id="alternate", quality="UNRELIABLE")
    forecast = replace(ia.entity_interactions[0], trajectory_id="alternate", quality="UNRELIABLE")
    ts = replace(ts, trajectories=(*ts.trajectories, alternate))
    ia = replace(ia, entity_interactions=(*ia.entity_interactions, forecast))
    assert assess((s, c, ts, ia)).risk_level == RiskLevel.UNDETERMINED


def test_rising_and_falling_are_unsmoothed(geometry):
    outside = case(
        geometry, kind="REMAIN_OUTSIDE", entry=None, envelope="NO_INTERSECTION_WITHIN_ENVELOPE"
    )
    engine = RuleBasedRiskEngine(RiskConfig())
    engine.assess(*outside)
    inside = advance(case(geometry, relation=Relation.INSIDE))
    assert engine.assess(*inside).assessments[0].trend == RiskTrend.RISING
    outside_later = advance(outside, 200_000_000)
    assert engine.assess(*outside_later).assessments[0].trend == RiskTrend.FALLING


@pytest.mark.parametrize("missing", ["depth", "semantics"])
def test_image_occupancy_independent_of_optional_sensing(geometry, missing):
    s, c, _, _ = case(geometry, relation=Relation.INSIDE)
    e = s.entities[0]
    e = replace(e, **({"depth": None} if missing == "depth" else {"semantic_evidence": None}))
    assert assess((replace(s, entities=(e,)), c, None, None)).risk_level == RiskLevel.HIGH


def test_duplicate_identity_and_bounds_rejected(geometry):
    s, c, ts, ia = case(geometry)
    with pytest.raises(ValueError, match="Duplicate"):
        assess((replace(s, entities=(s.entities[0], s.entities[0])), c, ts, ia))
    with pytest.raises(ValueError, match="bound"):
        RuleBasedRiskEngine(RiskConfig(max_entities=1)).assess(
            replace(s, entities=(s.entities[0], s.entities[0])), c, ts, ia
        )


def test_draft_review_windows_and_read_only_server(tmp_path):
    import json
    import sys
    from http.server import ThreadingHTTPServer
    from pathlib import Path
    from threading import Thread
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen

    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
    from risk_review import handler, windows

    rows = windows(600)
    assert len(rows) == 30 and rows[-1]["end_seconds"] == 600
    assert all(
        r["review_status"] == "DRAFT_REVIEW_REQUIRED"
        and r["review_label"] is None
        and r["end_seconds"] - r["start_seconds"] == 6
        for r in rows
    )
    (tmp_path / "video.mp4").write_bytes(b"0123456789")
    (tmp_path / "index.html").write_text("review")
    (tmp_path / "manifest.json").write_text(
        json.dumps({"source_path": str(tmp_path / "video.mp4")})
    )
    with ThreadingHTTPServer(("127.0.0.1", 0), handler(tmp_path)) as server:
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(
                Request(base + "/video", headers={"Range": "bytes=2-5"}), timeout=3
            ) as response:
                assert response.status == 206 and response.read() == b"2345"
            for path, status in (("/../private", 404), ("/video", 416)):
                with pytest.raises(HTTPError) as error:
                    urlopen(Request(base + path, headers={"Range": "bytes=20-30"}), timeout=3)
                assert error.value.code == status
            with pytest.raises(HTTPError) as error:
                urlopen(Request(base, data=b"no writes", method="POST"), timeout=3)
            assert error.value.code == 501
        finally:
            server.shutdown()
            worker.join(timeout=3)
