"""Causal episode, expiry, isolation and interruption-load regressions."""

from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest

from perception_lab.attention import (
    CooldownAttentionPolicy,
    NaiveAttentionPolicy,
    NoveltyEscalationAttentionPolicy,
)
from perception_lab.attention_config import AttentionConfig
from perception_lab.attention_overlay import draw_attention
from perception_lab.attention_types import AttentionAction, AudioChannelState
from perception_lab.contracts import ComponentProvenance, LabError
from perception_lab.risk_types import (
    RiskAssessment,
    RiskAssessmentSet,
    RiskLevel,
    RiskQuality,
    RiskTrend,
)
from perception_lab.world_types import WorldEntityId

P = ComponentProvenance("fixture", "risk")


def risks(t=0, levels=(RiskLevel.HIGH,), quality=RiskQuality.DEGRADED, session="test", first_id=1):
    rows = tuple(
        RiskAssessment(
            WorldEntityId(session, first_id + i),
            t,
            t + 500_000_000,
            level,
            quality,
            (),
            (),
            ("CURRENT_OCCUPANCY",),
            None,
            (),
            ("CURRENT_OCCUPANCY",),
            RiskTrend.STABLE,
            (P,),
            "fixture",
            "UNVERIFIED",
        )
        for i, level in enumerate(levels)
    )
    return RiskAssessmentSet(session, t, t + 500_000_000, rows, (), (), (), (), P, "fixture", P)


def action(output):
    return output.selected[0].decision


def test_first_announcement_unchanged_suppression_and_immutability():
    engine = NoveltyEscalationAttentionPolicy()
    original = risks()
    first = engine.decide(original)
    assert action(first) == AttentionAction.ANNOUNCE
    assert first.selected[0].novelty == "NEW"
    assert first.selected[0].event.valid_until_ns == 500_000_000
    for i in range(1, 101):
        result = engine.decide(risks(i * 10_000_000))
        assert action(result) == AttentionAction.SILENT
        assert result.suppressed[0].reason == "COOLDOWN_ACTIVE"
    assert original == risks()
    with pytest.raises(FrozenInstanceError):
        first.scene_status = "SAFE"


@pytest.mark.parametrize(
    "before,after", [(RiskLevel.HIGH, RiskLevel.SEVERE), (RiskLevel.ELEVATED, RiskLevel.HIGH)]
)
def test_escalation_bypasses_normal_cooldown(before, after):
    engine = NoveltyEscalationAttentionPolicy()
    engine.decide(risks(levels=(before,)))
    result = engine.decide(risks(100_000_000, (after,)))
    assert action(result) == AttentionAction.ESCALATE
    assert result.selected[0].cooldown_active
    assert "HIGHER_PRIORITY_OVERRIDE" in result.selected[0].reason_codes


@pytest.mark.parametrize(
    "level,quality,reason",
    [
        (RiskLevel.UNDETERMINED, RiskQuality.GOOD, "UNDETERMINED_RISK"),
        (RiskLevel.LOW, RiskQuality.GOOD, "ENTITY_RESOLVED"),
        (RiskLevel.HIGH, RiskQuality.INSUFFICIENT, "LOW_EVIDENCE_QUALITY"),
    ],
)
def test_unknown_low_and_failed_quality_silent_with_reason(level, quality, reason):
    result = NoveltyEscalationAttentionPolicy().decide(risks(levels=(level,), quality=quality))
    assert action(result) == AttentionAction.SILENT
    assert result.suppressed[0].reason == reason
    assert "NO_INTERRUPT_NOT_A_SAFETY_VERDICT" in result.selected[0].reason_codes


def test_explicit_degraded_policy():
    engine = NoveltyEscalationAttentionPolicy(AttentionConfig(allow_degraded=False))
    assert engine.decide(risks()).suppressed[0].reason == "LOW_EVIDENCE_QUALITY"
    assert action(engine.decide(risks(1, quality=RiskQuality.GOOD))) == AttentionAction.ANNOUNCE


def test_duplicate_and_out_of_order_do_not_reemit_or_corrupt():
    engine = NoveltyEscalationAttentionPolicy()
    engine.decide(risks(100))
    assert engine.decide(risks(100)).suppressed[0].reason == "DUPLICATE_STATE"
    with pytest.raises(ValueError, match="backwards"):
        engine.decide(risks(99))
    assert action(engine.decide(risks(101))) == AttentionAction.SILENT
    engine.reset()
    assert action(engine.decide(risks(0))) == AttentionAction.ANNOUNCE


def test_expired_event_never_released_from_busy_backlog():
    engine = NoveltyEscalationAttentionPolicy()
    assert engine.decide(risks(), AudioChannelState(True, 4)).suppressed[0].reason == "AUDIO_BUSY"
    stale = risks(1)
    assert engine.decide(stale, now_ns=600_000_000).suppressed[0].reason == "EVENT_EXPIRED"
    assert action(engine.decide(risks(700_000_000))) == AttentionAction.ANNOUNCE


def test_priority_preemption_intent():
    engine = NoveltyEscalationAttentionPolicy()
    engine.decide(risks(levels=(RiskLevel.ELEVATED,)))
    result = engine.decide(risks(1, (RiskLevel.HIGH,)), AudioChannelState(True, 2))
    assert action(result) == AttentionAction.ESCALATE
    assert "PREEMPT_AUDIO_INTENT" in result.selected[0].reason_codes


def test_ranking_is_independent_of_input_order():
    value = risks(levels=(RiskLevel.ELEVATED, RiskLevel.HIGH, RiskLevel.HIGH))
    a = NoveltyEscalationAttentionPolicy().decide(value)
    b = NoveltyEscalationAttentionPolicy().decide(
        replace(value, assessments=value.assessments[::-1])
    )
    assert a == b
    assert a.selected[0].entity_id.serial == 2
    assert len(a.suppressed) == 2


def test_crowd_global_budget():
    engine = NoveltyEscalationAttentionPolicy()
    selected = []
    for t in range(60):
        result = engine.decide(risks(t * 1_000_000_000, (RiskLevel.ELEVATED,) * 50))
        assert len(result.selected) == 1
        selected += [d for d in result.selected if d.decision != AttentionAction.SILENT]
    assert len(selected) == 6
    assert engine.history_size == 50
    assert engine.scene_history_size <= 10


def test_rate_override_is_bounded_even_when_ids_churn():
    engine = NoveltyEscalationAttentionPolicy(AttentionConfig(max_interruptions=1))
    outputs = [
        engine.decide(risks(i, (level,), first_id=i + 1))
        for i, level in enumerate(
            [RiskLevel.ELEVATED, RiskLevel.HIGH, RiskLevel.SEVERE] + [RiskLevel.SEVERE] * 100
        )
    ]
    assert sum(action(o) != AttentionAction.SILENT for o in outputs) == 3


def test_persistence_repeat_requires_more_than_cooldown():
    engine = NoveltyEscalationAttentionPolicy()
    engine.decide(risks())
    actions = [action(engine.decide(risks(t * 1_000_000_000))) for t in range(1, 31)]
    assert actions[:-1] == [AttentionAction.SILENT] * 29
    assert actions[-1] == AttentionAction.REPEAT


def test_deescalation_oscillation_does_not_repeatedly_escalate():
    engine = NoveltyEscalationAttentionPolicy()
    outputs = [
        engine.decide(risks(i * 100_000_000, (level,)))
        for i, level in enumerate([RiskLevel.ELEVATED, RiskLevel.HIGH] * 50)
    ]
    assert sum(action(o) == AttentionAction.ESCALATE for o in outputs) == 1


def test_disappearance_reappearance_and_session_isolation():
    engine = NoveltyEscalationAttentionPolicy()
    first = engine.decide(risks()).selected[0].event.episode_id
    assert action(engine.decide(risks(1, ()))) == AttentionAction.SILENT
    result = engine.decide(risks(6_000_000_000))
    assert action(result) == AttentionAction.ANNOUNCE
    assert result.selected[0].novelty == "REAPPEARED"
    assert result.selected[0].event.episode_id != first
    assert action(engine.decide(risks(session="different"))) == AttentionAction.ANNOUNCE
    assert engine.history_size == 1


def test_id_switch_keeps_identity_separate():
    engine = NoveltyEscalationAttentionPolicy()
    first = engine.decide(risks()).selected[0]
    second = engine.decide(risks(3_000_000_000, first_id=2)).selected[0]
    assert first.entity_id != second.entity_id
    assert first.event.episode_id != second.event.episode_id


@pytest.mark.parametrize("bad", ["duplicate", "foreign", "timestamp", "schema", "bound"])
def test_invalid_input_rejected_before_mutation(bad):
    value = risks()
    if bad == "duplicate":
        value = replace(value, assessments=value.assessments * 2)
    elif bad == "foreign":
        value = replace(value, session_id="other")
    elif bad == "timestamp":
        value = replace(value, state_timestamp=1)
    elif bad == "schema":
        value = replace(value, schema_version=2)
    else:
        value = risks(levels=(RiskLevel.HIGH,) * 513)
    engine = NoveltyEscalationAttentionPolicy()
    with pytest.raises(ValueError):
        engine.decide(value)
    assert engine.history_size == 0


@pytest.mark.parametrize(
    "factory", [NaiveAttentionPolicy, CooldownAttentionPolicy, NoveltyEscalationAttentionPolicy]
)
def test_policy_swap_and_alternate_risk_producer(factory):
    value = replace(risks(), provenance=ComponentProvenance("alternate-risk", "risk"))
    result = factory().decide(value)
    assert result.schema_version == 1
    assert result.risk_provenance == value.provenance
    assert action(result) == AttentionAction.ANNOUNCE


def test_conservative_only_changes_interruption_threshold():
    engine = NoveltyEscalationAttentionPolicy(AttentionConfig(mode="CONSERVATIVE_ATTENTION"))
    assert action(engine.decide(risks(levels=(RiskLevel.ELEVATED,)))) == AttentionAction.SILENT
    assert action(engine.decide(risks(1))) == AttentionAction.ANNOUNCE


def test_history_bounded_with_entity_churn():
    engine = NoveltyEscalationAttentionPolicy(AttentionConfig(max_entities=10))
    for i in range(100):
        engine.decide(risks(i * 1_000_000, first_id=i))
        assert engine.history_size <= 10
    engine.decide(risks(100_000_000_000, ()))
    assert engine.history_size == 0


def test_overlay_preserves_source_pixels():
    pixels = np.zeros((240, 640, 3), dtype=np.uint8)
    image = draw_attention(pixels, NoveltyEscalationAttentionPolicy().decide(risks()))
    assert image.any() and not pixels.any()


def test_pipeline_swap_recording_and_cleanup(make_pipeline):
    from test_pipeline import records

    from perception_lab.sources import SyntheticSource

    class Replacement:
        def __init__(self):
            self.delegate = CooldownAttentionPolicy()
            self.calls = self.resets = 0

        def decide(self, risk, **kwargs):
            self.calls += 1
            return self.delegate.decide(risk, **kwargs)

        def reset(self):
            self.resets += 1
            self.delegate.reset()

    engine = Replacement()
    pipeline, recorder = make_pipeline(
        {"world_model": {}, "risk": {}, "attention": {}, "record_session": True},
        attention_engine=engine,
    )
    manifest = pipeline.run(SyntheticSource(iter([0, 33_333_333])))
    assert engine.calls == 2 and engine.resets == 1
    assert manifest["schema_version"] == 11
    assert manifest["summary"]["attention_decision_sets_published"] == 2
    frames = [r for r in records(recorder) if r["type"] == "frame_result"]
    assert len(frames) == 2
    assert all(r["attention_decision_set"]["scene_status"] == "SILENT" for r in frames)


def test_persistence_restarts_after_quality_gap():
    engine = NoveltyEscalationAttentionPolicy()
    engine.decide(risks())
    for t in range(1, 31):
        quality = RiskQuality.INSUFFICIENT if t == 29 else RiskQuality.DEGRADED
        result = engine.decide(risks(t * 1_000_000_000, quality=quality))
    assert action(result) == AttentionAction.SILENT


def test_event_identity_stable_during_silence_distinct_for_escalation():
    engine = NoveltyEscalationAttentionPolicy()
    first = engine.decide(risks()).selected[0].event
    second = engine.decide(risks(1)).suppressed[0].decision.event
    assert first == second
    third = engine.decide(risks(2, (RiskLevel.SEVERE,))).selected[0].event
    assert third.episode_id == first.episode_id and third.event_id != first.event_id


def test_changed_reason_family_is_observable_without_forcing_repeat():
    engine = NoveltyEscalationAttentionPolicy()
    engine.decide(risks())
    value = risks(1)
    value = replace(
        value, assessments=(replace(value.assessments[0], reason_codes=("PREDICTED_ENTRY",)),)
    )
    output = engine.decide(value)
    assert action(output) == AttentionAction.SILENT
    assert output.suppressed[0].decision.novelty == "CHANGED"


def test_short_event_lifetime_rejects_delayed_long_lived_risk():
    engine = NoveltyEscalationAttentionPolicy(AttentionConfig(event_validity_ns=10))
    assert engine.decide(risks(), now_ns=11).suppressed[0].reason == "EVENT_EXPIRED"


def test_first_stronger_candidate_can_preempt_busy_lower_priority():
    result = NoveltyEscalationAttentionPolicy().decide(risks(), AudioChannelState(True, 2))
    assert action(result) == AttentionAction.ANNOUNCE
    assert "PREEMPT_AUDIO_INTENT" in result.selected[0].reason_codes


def test_new_entity_priority_reversal_bypasses_scene_cooldown():
    engine = NoveltyEscalationAttentionPolicy()
    engine.decide(risks(levels=(RiskLevel.ELEVATED,)))
    result = engine.decide(risks(1, (RiskLevel.ELEVATED, RiskLevel.HIGH)))
    assert result.selected[0].entity_id.serial == 2
    assert "HIGHER_PRIORITY_OVERRIDE" in result.selected[0].reason_codes


@pytest.mark.parametrize(
    "kwargs",
    [{"cooldown_ns": 0}, {"max_entities": 513}, {"unknown": 1}, {"allow_degraded": "true"}],
)
def test_config_rejects_invalid_or_untyped_settings(kwargs):
    with pytest.raises(ValueError):
        AttentionConfig.model_validate(kwargs)


def test_benchmark_late_attention_is_not_negative_duration():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
    from attention_benchmark import AttentionProxy

    from perception_lab.interaction_config import InteractionConfig

    proxy = AttentionProxy(InteractionConfig())
    proxy.on_evaluated(
        {
            "start": 0,
            "entry": 10,
            "risk": "HIGH",
            "sensitivity": [],
            "attention": {"NOVELTY_ESCALATION": False},
            "first_attention": {"NOVELTY_ESCALATION": 20},
        },
        True,
        True,
    )
    result = proxy.report()["attention_proxy"]["NOVELTY_ESCALATION"]
    assert result["late_attention_delay_proxy"]["mean_ns"] == 10
    assert result["events"] == {"FN": 1}


def test_window_sampling_preserves_timestamps_and_closes_source():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
    from attention_benchmark import WindowSource

    from perception_lab.sources import SyntheticSource

    source = SyntheticSource(iter(range(0, 2_000_000_000, 100_000_000)))
    filtered = WindowSource(source, [{"start_seconds": 0.5, "end_seconds": 1.1}])
    assert [f.identity.observation_ns for f in filtered] == [500_000_000, 700_000_000, 900_000_000]
    filtered.close()


def test_review_packet_keeps_labels_draft_and_original_unchanged(tmp_path):
    import json
    import sys
    from dataclasses import asdict
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
    from attention_review import prepare

    source = tmp_path / "source"
    source.mkdir()
    manifest = {"windows": [{"start_seconds": 0, "end_seconds": 6}], "source_path": "private"}
    original = json.dumps(manifest)
    (source / "manifest.json").write_text(original)
    timeline = tmp_path / "timeline.jsonl"
    timeline.write_text(
        json.dumps(
            {"NOVELTY_ESCALATION": asdict(NoveltyEscalationAttentionPolicy().decide(risks()))}
        )
        + "\n"
    )
    packet = prepare(source, timeline, tmp_path / "review")
    assert packet["windows"][0]["review_label"] is None
    assert packet["windows"][0]["review_status"] == "DRAFT_REVIEW_REQUIRED"
    assert packet["attention_policy_validated_with_humans"] is False
    assert (source / "manifest.json").read_text() == original


@pytest.mark.parametrize("mode,expected", [("REALTIME", "SILENT"), ("OFFLINE_REPLAY", "ANNOUNCE")])
def test_pipeline_accounts_for_processing_age_before_interruption(
    make_pipeline, monkeypatch, mode, expected
):
    from conftest import records
    from test_pipeline import SimulatedClock

    from perception_lab.sources import SyntheticSource

    clock = SimulatedClock()
    monkeypatch.setattr("perception_lab.sources.processing_ns", clock)

    class SlowRisk:
        def assess(self, state, corridor, trajectories, interaction):
            clock.now += 1_000_000_000
            return risks(state.state_timestamp, session=state.session_id)

        def reset(self):
            pass

    config = {"world_model": {}, "risk": {}, "attention": {}, "record_session": True, "mode": mode}
    if mode == "REALTIME":
        config.update(drop_policy="LATEST_FRAME", max_staleness_ns=2_000_000_000)
    pipeline, recorder = make_pipeline(
        config, risk_engine=SlowRisk(), clock=clock, sleep=clock.sleep
    )
    manifest = pipeline.run(SyntheticSource(iter([0])))
    assert manifest["summary"]["frame_counts"]["processed"] == 1
    result = next(r for r in records(recorder) if r["type"] == "frame_result")
    attention = result["attention_decision_set"]
    assert attention["selected"][0]["decision"] == expected
    if mode == "REALTIME":
        assert attention["suppressed"][0]["reason"] == "EVENT_EXPIRED"


@pytest.mark.parametrize("failing", ["attention", "risk"])
def test_component_reset_failure_still_finalizes_recording(make_pipeline, failing):
    from perception_lab.risk import RuleBasedRiskEngine
    from perception_lab.risk_config import RiskConfig
    from perception_lab.sources import SyntheticSource

    class FailingAttention(NoveltyEscalationAttentionPolicy):
        def reset(self):
            if getattr(self, "fail_reset", False):
                raise RuntimeError("attention reset failure")
            super().reset()

    class FailingRisk(RuleBasedRiskEngine):
        def reset(self):
            if getattr(self, "fail_reset", False):
                raise RuntimeError("risk reset failure")
            super().reset()

    attention = FailingAttention()
    risk = FailingRisk(RiskConfig())
    pipeline, recorder = make_pipeline(
        {"world_model": {}, "risk": {}, "attention": {}, "record_session": True},
        attention_engine=attention,
        risk_engine=risk,
    )

    def listener(event):
        if event.kind == "FrameCompleted":
            (attention if failing == "attention" else risk).fail_reset = True

    pipeline.listener = listener
    source = SyntheticSource(iter([0]))
    with pytest.raises(LabError, match=failing.upper() + "_RESET_FAILED"):
        pipeline.run(source)
    assert recorder.closed and source.closed
    assert recorder.manifest["termination_reason"] == "FATAL"
    assert recorder.manifest["failure"] == failing.upper() + "_RESET_FAILED"
