from pathlib import Path
from time import perf_counter_ns
from types import SimpleNamespace

import pytest
from test_qualification_tools import tool
from test_tracking import identity


def test_gateway_rejection_observation_never_adds_speech_or_changes_baseline(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    worker = tool("alpha_field_worker")
    result = SimpleNamespace(
        identity=identity(0),
        world_state=None,
        width=640,
        height=480,
        camera_orientation=None,
        camera_view_quality=None,
        user_motion_heading=None,
        scene_capability=None,
        errors=(),
        warnings=(),
    )
    for field in (
        "detector",
        "tracks",
        "corridor_analysis",
        "trajectory_set",
        "interaction_analysis",
        "risk_assessment_set",
        "attention_decision_set",
    ):
        setattr(result, field, None)
    result.alert_output_set = SimpleNamespace(outputs=())
    source = SimpleNamespace(active=(0, perf_counter_ns()), session_id="session")
    baseline = worker.project(result, source)
    result.alert_output_set = None
    assert baseline["field_alerts"] == []
    assert "gateway_rejections" not in baseline
    result.alert_output_set = SimpleNamespace(
        outputs=[SimpleNamespace(delivered=False, intent=None, presentation=None)]
    )
    # The normal projector also serializes output types; make this fixture portable.
    original = worker.compact_alpha
    worker.compact_alpha = lambda value: (
        None if isinstance(value, SimpleNamespace) else original(value)
    )
    try:
        observed = worker.project(result, source, True)
    finally:
        worker.compact_alpha = original
    assert observed["field_alerts"] == []
    assert (
        observed["gateway_rejections"][0]["reason"] == "UPSTREAM_NOT_DELIVERED_OR_MISSING_LINEAGE"
    )


def test_budget_keeps_partial_evidence_without_mutating_tracker_snapshot(monkeypatch):
    import json

    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    worker = tool("alpha_field_worker")
    monkeypatch.setattr(
        worker,
        "object_diagnostics",
        lambda result: {"objects": [{"entity_id": i, "evidence": "x" * 10000} for i in range(3)]},
    )
    tracking = {"cost_observations": [{"reason": "CENTER_DISTANCE_GATE"} for _ in range(64)]}
    payload = worker.bounded_object_evidence(None, tracking, [])
    assert 0 < len(payload["objects"]) < 3
    assert len(json.dumps(payload).encode()) < 24500
    assert payload["budget_omissions"]["objects"] > 0
    assert len(tracking["cost_observations"]) == 64


@pytest.mark.parametrize(
    "session,captures,expected",
    [
        ("other", [(0, 1000000000)], "SESSION_OR_PRESENTATION_LINEAGE_MISMATCH"),
        ("session", [], "SOURCE_CAPTURE_NOT_RETAINED"),
        ("session", [(0, 0)], "INVALID_STATE_OR_EXPIRED_DEADLINE"),
        ("session", [(0, 1000000000)], None),
    ],
)
def test_gateway_lineage_capture_and_expiry_rejections(monkeypatch, session, captures, expected):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    worker = tool("alpha_field_worker")
    monkeypatch.setattr(worker, "perf_counter_ns", lambda: 1000000000)
    monkeypatch.setattr(worker, "compact_alpha", lambda value: None)
    lineage = object()
    intent = SimpleNamespace(
        session_id=session,
        alert_id="alert",
        lineage=lineage,
        source_observation_ns=0,
        state_timestamp=0,
        reason_codes=(),
        semantic_level="GENERIC",
    )
    presentation = SimpleNamespace(
        alert_id="alert", lineage=lineage, valid_until_ns=500000000, speech_text="Object"
    )
    result = SimpleNamespace(
        identity=identity(0),
        world_state=None,
        width=640,
        height=480,
        camera_orientation=None,
        camera_view_quality=None,
        user_motion_heading=None,
        scene_capability=None,
        errors=(),
        warnings=(),
    )
    for field in (
        "detector",
        "tracks",
        "corridor_analysis",
        "trajectory_set",
        "interaction_analysis",
        "risk_assessment_set",
        "attention_decision_set",
    ):
        setattr(result, field, None)
    result.alert_output_set = SimpleNamespace(
        outputs=[SimpleNamespace(delivered=True, intent=intent, presentation=presentation)]
    )
    source = SimpleNamespace(
        active=(0, 1000000000), session_id="session", captures=captures, origin=0
    )
    observed = worker.project(result, source, True)
    if expected:
        assert observed["field_alerts"] == []
        assert observed["gateway_rejections"][0]["reason"] == expected
    else:
        assert observed["gateway_rejections"] == []
        assert observed["field_alerts"][0]["alert_id"] == "alert"
