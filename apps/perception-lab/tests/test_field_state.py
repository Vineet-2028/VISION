import pytest

from perception_lab.field_protocol import PROTOCOL, ClockEstimate, FrameHeader, SessionStart
from perception_lab.field_state import FieldSession, LatestSlot


def session():
    return FieldSession(
        SessionStart(
            protocol_version=PROTOCOL,
            client_version="test",
            device_id="ephemeral",
            mode="ANDROID_FIELD_HARNESS",
            width=640,
            height=480,
            format="JPEG",
            capabilities=["CAMERA_REALTIME_CLOCK", "NO_AUDIO"],
        ),
        "fixture-hash",
        1_000_000_000,
    )


def test_recording_byte_budget_preserves_existing_evidence_and_stops_cleanly(monkeypatch):
    import io
    import json
    import zipfile

    from perception_lab import field_state
    from perception_lab.field_export import export_session

    monkeypatch.setattr(field_state, "MAX_RECORDED_EVENT_BYTES", 256)
    state = session()
    state.recording = True
    state.record("TEST", 1, {"reason": "x" * 100})
    assert len(state.events) == 1
    state.record("TEST", 2, {"reason": "x" * 100})
    assert len(state.events) == 1
    assert state.recording_full and not state.recording
    assert state.recorded_event_bytes <= 256
    with zipfile.ZipFile(io.BytesIO(export_session(state, 3))) as archive:
        assert len(archive.read("events.jsonl")) == state.recorded_event_bytes
        assert json.loads(archive.read("manifest.json"))["recording_full"]
    # Inference/event counters continue even after optional recording has stopped.
    state.record("TEST", 3, {"reason": "later"})
    assert state.counts["TEST"] == 3
    assert len(state.events) == 1


def frame(s, sequence=1, camera=1_000_000_000):
    return FrameHeader(
        protocol_version=PROTOCOL,
        session_id=s.session_id,
        sequence=sequence,
        camera_ns=str(camera),
        capture_ns=str(camera),
        send_ns=str(camera),
        sync_version=1,
        rotation=0,
        width=640,
        height=480,
        format="JPEG",
        jpeg_quality=75,
    )


def test_replayed_frame_cannot_advance_session():
    s = session()
    s.estimates.append(ClockEstimate(0, 0, 0, 1_000_000_000, 1))
    assert s.accept_frame(frame(s), 1_010_000_000) == 999_990_000
    with pytest.raises(ValueError, match="OUT_OF_ORDER"):
        s.accept_frame(frame(s), 1_020_000_000)
    assert s.last_sequence == 1


def test_resynchronization_cannot_move_admitted_capture_backwards():
    s = session()
    s.estimates.append(ClockEstimate(0, 0, 0, 1_000_000_000, 1))
    first = s.accept_frame(frame(s), 1_010_000_000)
    s.estimates.append(ClockEstimate(-100_000_000, 0, 0, 1_040_000_000, 2))
    newer = frame(s, 2, 1_050_000_000).model_copy(update={"sync_version": 2})
    with pytest.raises(ValueError, match="MAPPED_CAPTURE_REGRESSED"):
        s.accept_frame(newer, 1_060_000_000)
    assert s.last_sequence == 1 and s.last_host_capture_ns == first
    later = frame(s, 2, 1_150_000_000).model_copy(update={"sync_version": 2})
    assert s.accept_frame(later, 1_160_000_000) > first


def test_active_capture_survives_a_burst_of_newer_admissions():
    s = session()
    start = 1_000_000_000
    s.estimates.append(ClockEstimate(0, 0, 0, start, 1))
    captured = s.accept_frame(frame(s), start)
    s.begin_inference(1, captured)
    for seq in range(2, 24):
        now = start + seq * 1_000_000
        s.accept_frame(frame(s, seq, now), now)
    s.publish_result(
        session_id=s.session_id,
        sequence=1,
        capture_host_ns=captured,
        scene={"frame": 1},
        now_ns=start + 25_000_000,
    )
    s.end_inference()
    assert s.snapshot(start + 26_000_000)["result"]["sequence"] == 1
    compact = s.snapshot(start + 26_000_000, alerts_only=True)
    assert compact["result"] == {
        "sequence": 1,
        "age_at_response_ns": "26000000",
        "field_alerts": [],
    }
    assert s.snapshot(start + 500_000_000, alerts_only=True)["result"] is None


def test_closed_session_rejects_late_events():
    s = session()
    s.recording = True
    s.close()
    with pytest.raises(ValueError, match="SESSION_CLOSED"):
        s.record("START_SCENARIO", 1_000_000_001, {"scenario": "LOW_LIGHT"})
    assert not s.events and not s.counts
    assert not s.snapshot(1_000_000_001)["recording"]


def test_speech_callbacks_require_published_alert_and_deduplicate_per_kind():
    s = session()
    now = 1_000_000_000
    s.estimates.append(ClockEstimate(0, 0, 0, now, 1))
    captured = s.accept_frame(frame(s), now)
    with pytest.raises(ValueError, match="UNRECOGNIZED"):
        s.record_speech("TTS_COMPLETED", "unexpected", now, now)
    s.recording = True
    s.publish_result(
        session_id=s.session_id,
        sequence=1,
        capture_host_ns=captured,
        scene={"field_alerts": [{"alert_id": "actual"}]},
        now_ns=now,
    )
    for _ in range(2):
        s.record_speech("APP_TTS_PLAYBACK_START_ESTIMATE", "actual", now + 5, now + 10)
    assert s.counts["APP_TTS_PLAYBACK_START_ESTIMATE"] == 1
    assert s.events[-1]["client_event_ns"] == str(now + 5)
    s.close()
    with pytest.raises(ValueError, match="UNRECOGNIZED"):
        s.record_speech("TTS_COMPLETED", "actual", now + 15, now + 20)


def test_expired_input_does_not_consume_sequence():
    s = session()
    s.estimates.append(ClockEstimate(0, 0, 0, 1_000_000_000, 1))
    with pytest.raises(ValueError, match="FRAME_EXPIRED"):
        s.accept_frame(frame(s), 1_500_000_000)
    assert s.last_sequence == -1


@pytest.mark.parametrize("delay_ms", [50, 100, 250, 500, 1000])
def test_transport_delay_matrix_preserves_source_age_and_rejects_expiry(delay_ms):
    s = session()
    s.estimates.append(ClockEstimate(0, 10_000_000, 20_000_000, 1_000_000_000, 1))
    arrived = 1_000_000_000 + delay_ms * 1_000_000
    if delay_ms >= 500:
        with pytest.raises(ValueError, match="FRAME_EXPIRED"):
            s.accept_frame(frame(s), arrived)
        assert s.last_sequence == -1
        assert s.snapshot(arrived)["result"] is None
        return
    capture = s.accept_frame(frame(s), arrived)
    # Offset uncertainty and drift make the timestamp older, never fresh at arrival.
    assert arrived - capture >= (delay_ms + 10) * 1_000_000
    s.publish_result(
        session_id=s.session_id,
        sequence=1,
        capture_host_ns=capture,
        scene={"identity": {"sequence": 1}},
        now_ns=arrived + 10_000_000,
    )
    snapshot = s.snapshot(arrived + 20_000_000)
    assert int(snapshot["result"]["age_at_response_ns"]) >= (delay_ms + 30) * 1_000_000
    assert s.snapshot(capture + 500_000_000)["result"] is None


def test_close_discards_scene_and_rejects_input():
    s = session()
    publish_fixture(s)
    s.close()
    assert s.snapshot(1_000_000_001)["result"] is None
    with pytest.raises(ValueError, match="WRONG_SESSION"):
        s.accept_frame(frame(s), 1_000_000_001)


def test_disconnect_hides_scene_without_dashboard_refreshing_client_liveness():
    s = session()
    publish_fixture(s)
    assert s.snapshot(4_000_000_001)["result"] is None
    assert s.last_client_ns == 1_010_000_000


def publish_fixture(s, sequence=1, camera=1_000_000_000):
    if not s.estimates:
        s.estimates.append(ClockEstimate(0, 0, 0, 1_000_000_000, 1))
    capture = s.accept_frame(frame(s, sequence, camera), camera + 10_000_000)
    payload = {"identity": {"sequence": sequence}}
    s.publish_result(
        session_id=s.session_id,
        sequence=sequence,
        capture_host_ns=capture,
        scene=payload,
        now_ns=camera + 20_000_000,
    )
    return capture, payload


def test_repeated_status_polling_cannot_refresh_cached_scene():
    s = session()
    captured, _ = publish_fixture(s)
    first = s.snapshot(captured + 100_000_000)
    later = s.snapshot(captured + 400_000_000)
    assert first["result"]["age_at_response_ns"] == "100000000"
    assert later["result"]["age_at_response_ns"] == "400000000"
    expired = s.snapshot(captured + 500_000_000)
    assert expired["status"] == "CONNECTED"
    assert expired["result"] is None
    assert expired["result_status"] == "EXPIRED_OR_FUTURE"


def test_published_scene_has_no_shared_mutable_payload():
    s = session()
    captured, original = publish_fixture(s)
    original["identity"]["sequence"] = 999
    first = s.snapshot(captured + 100_000_000)
    assert first["result"]["scene"]["identity"]["sequence"] == 1
    first["result"]["scene"]["identity"]["sequence"] = 999
    assert s.snapshot(captured + 200_000_000)["result"]["scene"]["identity"]["sequence"] == 1


def test_publication_rejects_wrong_session_capture_stale_and_replayed_results():
    s = session()
    capture, _ = publish_fixture(s)
    args = dict(
        session_id=s.session_id, sequence=1, capture_host_ns=capture, scene={}, now_ns=1_030_000_000
    )
    with pytest.raises(ValueError, match="OUT_OF_ORDER"):
        s.publish_result(**args)
    with pytest.raises(ValueError, match="WRONG_SESSION"):
        s.publish_result(**{**args, "session_id": "different"})
    with pytest.raises(ValueError, match="NOT_ADMITTED"):
        s.publish_result(**{**args, "sequence": 2})
    next_capture = s.accept_frame(frame(s, 2, 1_100_000_000), 1_110_000_000)
    args.update(sequence=2, capture_host_ns=next_capture)
    for now in [next_capture - 1, next_capture + 500_000_000]:
        with pytest.raises(ValueError, match="EXPIRED_OR_FUTURE"):
            s.publish_result(**{**args, "now_ns": now})


def test_recording_is_opt_in_bounded_and_preserves_server_event_identity():
    s = session()
    s.record("ignored", 1, {})
    assert not s.events
    s.recording = True
    s.record("capture", 2, {"kind": "spoof", "host_ns": "spoof"})
    assert s.events[0] == {"kind": "capture", "host_ns": "2"}
    for i in range(10_000):
        s.record("capture", i + 3, {})
    assert len(s.events) == 10_000
    assert s.recording_full and not s.recording
    assert s.events[0]["host_ns"] == "2"


def test_latest_slot_replaces_pending_without_growing_queue():
    slot = LatestSlot()
    for i in range(100):
        slot.put(i)
    assert slot.replaced == 99
    assert slot.take() == 99
    assert slot.take() is None


def test_sync_challenge_single_use_and_bounded():
    s = session()
    challenge = s.begin_sync(1000, 1110, 1120)
    key = str(challenge["challenge"])
    assert s.finish_sync(key, 1030, 1130).offset_ns == 100
    with pytest.raises(ValueError, match="UNKNOWN"):
        s.finish_sync(key, 1030, 1131)
    for i in range(20):
        s.begin_sync(i, i, i)
    assert len(s.challenges) == 8
