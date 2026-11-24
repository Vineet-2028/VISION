"""Presentation boundary regressions; software evidence, not language validation."""

from dataclasses import FrozenInstanceError, replace
from itertools import product

import pytest
from test_attention import risks

from perception_lab.alert_config import AlertConfig
from perception_lab.alert_presenter import NullAlertPresenter, RecordingAlertPresenter
from perception_lab.alert_renderer import EnglishV1AlertRenderer
from perception_lab.alerts import AlertEngine
from perception_lab.attention import (
    CooldownAttentionPolicy,
    NaiveAttentionPolicy,
    NoveltyEscalationAttentionPolicy,
)
from perception_lab.attention_types import AttentionAction, AttentionSemanticEvidence
from perception_lab.contracts import ComponentProvenance
from perception_lab.risk_types import RiskLevel
from perception_lab.world_types import WorldEntityId


def batch(t=0, **semantics):
    output = NoveltyEscalationAttentionPolicy().decide(risks(t))
    d = output.selected[0]
    if semantics:
        evidence = AttentionSemanticEvidence(
            d.entity_id,
            t,
            t + 500_000_000,
            quality="DEGRADED",
            provenance=(ComponentProvenance("fixture", "semantics"),),
            **semantics,
        )
        d = replace(d, semantic_evidence=evidence)
    return replace(output, selected=(d,))


@pytest.mark.parametrize(
    "category,direction,interaction,action",
    list(
        product(
            ("PERSON", "BICYCLE", "MOTORCYCLE", "VEHICLE", "OBSTACLE", "UNKNOWN"),
            ("LEFT", "RIGHT", "AHEAD", "UNKNOWN"),
            ("CROSSING", "APPROACHING", "IN_CORRIDOR", "STATIC_OBSTACLE", "GENERIC"),
            (AttentionAction.ANNOUNCE, AttentionAction.REPEAT, AttentionAction.ESCALATE),
        )
    ),
)
def test_template_matrix(category, direction, interaction, action):
    b = batch(category=category, direction=direction, interaction=interaction)
    b = replace(b, selected=(replace(b.selected[0], decision=action),))
    result = AlertEngine().process(b, now_ns=0).outputs[0]
    assert result.status == "READY"
    p = result.presentation
    noun = {
        "PERSON": "Person",
        "BICYCLE": "Bicycle",
        "MOTORCYCLE": "Motorcycle",
        "VEHICLE": "Vehicle",
        "OBSTACLE": "Obstacle",
        "UNKNOWN": "Object",
    }[category]
    suffix = {
        "CROSSING": ("crossing from left", "crossing from right", "crossing ahead", "crossing"),
        "APPROACHING": (
            "approaching left",
            "approaching right",
            "approaching ahead",
            "approaching",
        ),
        "IN_CORRIDOR": ("left", "right", "ahead", ""),
        "STATIC_OBSTACLE": ("left", "right", "ahead", ""),
        "GENERIC": ("left", "right", "ahead", ""),
    }[interaction][("LEFT", "RIGHT", "AHEAD", "UNKNOWN").index(direction)]
    assert p.speech_text == f"{noun} {suffix}".strip() + "."
    assert p.short_text == p.speech_text
    assert 1 <= p.word_count <= 5
    assert p.estimated_speech_seconds == p.word_count / 3
    assert p.style == (
        "EMPHASIS"
        if action == AttentionAction.ESCALATE
        else "FULL_REPEAT"
        if action == AttentionAction.REPEAT
        else "NORMAL"
    )
    assert all(
        word not in p.speech_text.lower()
        for word in ("safe", "move", "turn", "collision", "ttc", "corridor", "confidence", "meters")
    )


def test_unproven_bare_category_direction_not_used():
    b = batch()
    b = replace(b, selected=(replace(b.selected[0], category="BICYCLE", direction="RIGHT"),))
    assert AlertEngine().process(b, now_ns=0).outputs[0].presentation.speech_text == "Object."


@pytest.mark.parametrize(
    "mutation",
    [
        {"quality": "UNAVAILABLE"},
        {"valid_until_ns": 0},
        {"observed_ns": 1},
        {"entity_id": WorldEntityId("wrong", 1)},
        {"provenance": ()},
    ],
)
def test_unqualified_semantics_fall_back(mutation):
    b = batch(category="PERSON", direction="LEFT", interaction="CROSSING")
    d = b.selected[0]
    b = replace(
        b, selected=(replace(d, semantic_evidence=replace(d.semantic_evidence, **mutation)),)
    )
    assert AlertEngine().process(b, now_ns=0).outputs[0].presentation.speech_text == "Object."


@pytest.mark.parametrize("category", ["CAR", "BUS", "TRUCK"])
def test_vehicle_mapping(category):
    assert (
        AlertEngine()
        .process(batch(category=category), now_ns=0)
        .outputs[0]
        .presentation.speech_text
        == "Vehicle."
    )


@pytest.mark.parametrize("now", [500_000_000, 900_000_000])
def test_expired_before_render_no_text(now):
    sink = RecordingAlertPresenter()
    output = AlertEngine(presenter=sink).process(batch(), now_ns=now).outputs[0]
    assert output.status == "DROPPED_EXPIRED" and output.presentation is None
    assert sink.pending is None and not sink.history


def test_expiry_after_renderer_before_sink():
    sink = RecordingAlertPresenter()
    result = (
        AlertEngine(presenter=sink)
        .process(batch(), now_ns=0, delivery_clock=lambda: 500_000_000)
        .outputs[0]
    )
    assert result.status == "DROPPED_EXPIRED" and not result.delivered
    assert sink.pending is None


def test_pending_expiry_at_actual_consumption():
    sink = RecordingAlertPresenter()
    AlertEngine(presenter=sink).process(batch(), now_ns=0)
    assert sink.take(500_000_000).status == "DROPPED_EXPIRED"
    assert sink.take(500_000_001).status == "NO_PRESENTATION"


def test_delivery_age_includes_wait_after_generation():
    sink = RecordingAlertPresenter()
    engine = AlertEngine(presenter=sink)
    out = engine.process(batch(), now_ns=0, delivery_clock=lambda: 100).outputs[0]
    assert out.delivery_timestamp == 100 and out.source_age_at_delivery_ns == 100
    assert out.presentation_age_ns == 100
    consumed = sink.take(200)
    assert consumed.presentation_age_ns == 200 and consumed.source_age_at_delivery_ns == 200


@pytest.mark.parametrize(
    "updates",
    [
        {"state_timestamp": -1},
        {"session_id": ""},
        {"schema_version": 99},
    ],
)
def test_invalid_batch_rejected(updates):
    engine = AlertEngine()
    assert (
        engine.process(replace(batch(), **updates), now_ns=0).outputs[0].status == "DROPPED_INVALID"
    )
    assert engine.process(batch(), now_ns=0).outputs[0].delivered


def test_nonexistent_action_rejected():
    b = batch()
    b = replace(b, selected=(replace(b.selected[0], decision="SPEAK_ANYWAY"),))
    assert AlertEngine().process(b, now_ns=0).outputs[0].status == "DROPPED_INVALID"


def test_silent_does_not_render_or_deliver():
    b = NoveltyEscalationAttentionPolicy().decide(risks(levels=(RiskLevel.LOW,)))
    output = AlertEngine().process(b, now_ns=0).outputs[0]
    assert output.status == "NO_PRESENTATION" and output.presentation is None


def test_duplicate_decision_and_sink_rejection():
    engine = AlertEngine()
    b = batch()
    first = engine.process(b, now_ns=0).outputs[0]
    second = engine.process(b, now_ns=1).outputs[0]
    assert first.delivered and not second.delivered and second.status == "DROPPED_DUPLICATE"
    assert (
        engine.presenter.submit(first.intent, first.presentation, 2).status == "DROPPED_DUPLICATE"
    )


def test_latest_slot_supersession_no_backlog():
    sink = RecordingAlertPresenter()
    engine = AlertEngine(presenter=sink)
    old = engine.process(batch(), now_ns=0).outputs[0]
    b = batch(100)
    b = replace(b, selected=(replace(b.selected[0], decision=AttentionAction.ESCALATE),))
    latest = engine.process(b, now_ns=100).outputs[0]
    assert any(o.status == "DROPPED_SUPERSEDED" and o.intent == old.intent for o in sink.history)
    assert sink.take(101).intent == latest.intent
    assert sink.take(102).status == "NO_PRESENTATION"


def test_wrong_session_out_of_order_and_explicit_seek_reset():
    engine = AlertEngine()
    engine.process(batch(100), now_ns=100)
    assert engine.process(batch(), now_ns=101).outputs[0].status == "DROPPED_INVALID"
    assert (
        engine.process(replace(batch(102), session_id="wrong"), now_ns=102).outputs[0].status
        == "DROPPED_INVALID"
    )
    engine.reset()
    assert engine.process(batch(), now_ns=0).outputs[0].delivered


def test_source_age_and_deadline_use_oldest_reported_evidence():
    r = risks(300_000_000)
    r = replace(r, assessments=(replace(r.assessments[0], source_ages=(("track", 250_000_000),)),))
    b = NoveltyEscalationAttentionPolicy().decide(r)
    engine = AlertEngine()
    output = engine.process(b, now_ns=300_000_000).outputs[0]
    assert output.presentation.source_age_ns == 250_000_000
    assert output.intent.valid_until_ns == 550_000_000
    assert output.presentation.timing_status == "LATE_CANDIDATE"
    assert engine.process(b, now_ns=550_000_000).outputs[0].status == "DROPPED_EXPIRED"


def test_contract_immutability():
    out = AlertEngine().process(batch(), now_ns=0).outputs[0]
    with pytest.raises(FrozenInstanceError):
        out.intent.urgency = 99
    with pytest.raises(FrozenInstanceError):
        out.presentation.speech_text = "changed"


def test_long_phrase_rejected_without_truncating_semantics():
    engine = AlertEngine(AlertConfig(max_words=2))
    output = engine.process(
        batch(category="BICYCLE", direction="RIGHT", interaction="CROSSING"), now_ns=0
    ).outputs[0]
    assert output.status == "UNRENDERABLE" and not output.delivered


@pytest.mark.parametrize(
    "policy", [NaiveAttentionPolicy, CooldownAttentionPolicy, NoveltyEscalationAttentionPolicy]
)
def test_attention_policy_swap(policy):
    assert AlertEngine().process(policy().decide(risks()), now_ns=0).outputs[0].delivered


@pytest.mark.parametrize("sink", [RecordingAlertPresenter, NullAlertPresenter])
def test_presenter_and_renderer_swaps(sink):
    class OtherRenderer:
        def render(self, intent, now_ns):
            return replace(EnglishV1AlertRenderer().render(intent, now_ns), short_text="Object")

    out = (
        AlertEngine(renderer=OtherRenderer(), presenter=sink())
        .process(batch(), now_ns=0)
        .outputs[0]
    )
    assert out.presentation.short_text == "Object"
    assert out.delivered == (sink is RecordingAlertPresenter)


def test_bounded_history_rejects_evicted_old_ids():
    sink = RecordingAlertPresenter(2)
    engine = AlertEngine(presenter=sink)
    first = engine.process(batch(), now_ns=0).outputs[0]
    for t in range(1, 100):
        assert engine.process(batch(t), now_ns=t).outputs[0].delivered
    assert len(sink.history) == 2 and len(sink._ids) == 2
    assert not sink.submit(first.intent, first.presentation, 100).delivered


def test_excessive_selected_batch_rejected_without_reranking():
    b = batch()
    assert (
        AlertEngine().process(replace(b, selected=b.selected * 129), now_ns=0).outputs[0].status
        == "DROPPED_INVALID"
    )


def test_missing_semantic_source_age_remains_unavailable():
    b = batch()
    b = replace(b, selected=(replace(b.selected[0], source_observation_ns=None),))
    p = AlertEngine().process(b, now_ns=0).outputs[0].presentation
    assert p.source_age_ns is None and p.timing_status == "AGE_UNAVAILABLE"


def test_pipeline_records_schema12_and_cleans_up(make_pipeline):
    from test_pipeline import records

    from perception_lab.sources import SyntheticSource

    class Engine(AlertEngine):
        resets = 0

        def reset(self, session_id=None):
            super().reset(session_id)
            self.resets += 1

    engine = Engine()
    pipeline, recorder = make_pipeline(
        {"world_model": {}, "risk": {}, "attention": {}, "alerts": {}, "record_session": True},
        alert_engine=engine,
    )
    result = pipeline.run(SyntheticSource(iter([0, 33_333_333])))
    frames = [r for r in records(recorder) if r["type"] == "frame_result"]
    assert result["schema_version"] == 12 and len(frames) == 2
    assert all(
        f["schema_version"] == 12
        and f["alert_output_set"]["outputs"][0]["status"] == "NO_PRESENTATION"
        for f in frames
    )
    assert frames[0]["alert_output_set"]["mode"] == "OFFLINE_REPLAY_PRESENTATION"
    assert engine.resets == 3 and engine.session_id is None and recorder.closed


def test_alert_reset_failure_still_closes_recorder(make_pipeline):
    from perception_lab.contracts import LabError
    from perception_lab.sources import SyntheticSource

    class Broken(AlertEngine):
        def reset(self, session_id=None):
            if hasattr(self, "session_id") and self.session_id is not None and session_id is None:
                raise RuntimeError("injected cleanup failure")
            super().reset(session_id)

    pipeline, recorder = make_pipeline(
        {"world_model": {}, "risk": {}, "attention": {}, "alerts": {}, "record_session": True},
        alert_engine=Broken(),
    )
    with pytest.raises(LabError, match="ALERT_RESET_FAILED"):
        pipeline.run(SyntheticSource(iter([0])))
    assert recorder.closed


def test_overlay_is_additive():
    import numpy as np

    from perception_lab.alert_overlay import draw_alerts

    source = np.zeros((200, 800, 3), dtype=np.uint8)
    image = draw_alerts(source, AlertEngine().process(batch(), now_ns=0))
    assert image.any() and not source.any()


def test_alert_configuration_requires_attention():
    from pydantic import ValidationError

    from perception_lab.config import LabConfig

    with pytest.raises(ValidationError, match="Alerts require"):
        LabConfig.model_validate(
            {"input": "x", "calibration": "x", "intervals_ns": {"detector": 1}, "alerts": {}}
        )


def test_review_packet_preserves_draft_and_source(tmp_path):
    import importlib.util
    import json
    import sys
    from dataclasses import asdict
    from pathlib import Path

    tools = Path(__file__).resolve().parents[3] / "tools"
    sys.path.insert(0, str(tools))
    try:
        spec = importlib.util.spec_from_file_location("alert_review", tools / "alert_review.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = tmp_path / "source"
        source.mkdir()
        original = {"windows": [{"start_seconds": 0, "end_seconds": 1, "review_label": "OLD"}]}
        manifest = source / "manifest.json"
        manifest.write_text(json.dumps(original), encoding="utf-8")
        timeline = tmp_path / "timeline.jsonl"
        timeline.write_text(
            json.dumps(asdict(AlertEngine().process(batch(), now_ns=0))) + "\n", encoding="utf-8"
        )
        packet = module.prepare(source, timeline, tmp_path / "packet")
        assert packet["windows"][0]["review_label"] is None
        assert packet["windows"][0]["alert_timeline"][0]["outputs"][0]["status"] == "READY"
        assert json.loads(manifest.read_text()) == original
        assert not packet["alert_language_validated_with_users"]
    finally:
        sys.path.remove(str(tools))
