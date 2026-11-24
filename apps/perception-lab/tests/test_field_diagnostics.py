import json

from perception_lab.field_diagnostics import LossReason, stage_ledger


def test_empty_results_do_not_establish_detection_success_or_failure():
    ledger = stage_ledger({"tracks": [], "attention": None}, "session-a", 1)
    stages = {row["stage"]: row["evidence"] for row in ledger["stages"]}
    assert stages["TRACK_ASSOCIATION_GENERATION"] == "RESULT_AVAILABLE"
    assert stages["ATTENTION"] == "NOT_OBSERVED"
    assert ledger["first_proven_loss_reason"] == LossReason.UNKNOWN


def test_same_sequence_in_different_sessions_has_distinct_identity():
    assert stage_ledger({}, "a", 1)["event_id"] != stage_ledger({}, "b", 1)["event_id"]


def test_shadow_projection_is_bounded_and_does_not_copy_payloads():
    scene = {"tracks": ["PRIVATE" * 1000] * 10000, "field_alerts": []}
    ledger = stage_ledger(scene, "test", 1)
    encoded = json.dumps(ledger)
    assert len(encoded) < 2500
    assert "PRIVATE" not in encoded
    assert len(ledger["stages"]) == 16
    assert len(scene["tracks"]) == 10000
