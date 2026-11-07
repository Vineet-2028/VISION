import io
import json
import threading
import urllib.error
import urllib.request
import zipfile

import pytest

from perception_lab.field_gateway import FieldHTTPServer, Gateway
from perception_lab.field_protocol import PROTOCOL


def start_payload():
    return json.dumps(
        {
            "protocol_version": PROTOCOL,
            "client_version": "test",
            "device_id": "random-session-id",
            "mode": "DESKTOP_REALTIME",
            "width": 640,
            "height": 480,
            "format": "JPEG",
            "capabilities": ["NO_AUDIO"],
        }
    ).encode()


def test_start_cannot_silently_replace_active_session():
    gateway = Gateway("x" * 32, "fixture-hash")
    first = gateway.dispatch("POST", "/v1/session", start_payload(), 100)
    with pytest.raises(ValueError, match="ALREADY_ACTIVE"):
        gateway.dispatch("POST", "/v1/session", start_payload(), 101)
    first_close = json.dumps({"session_id": json.loads(first[1])["session_id"]}).encode()
    gateway.dispatch("POST", "/v1/close", first_close, 102)
    second = gateway.dispatch("POST", "/v1/session", start_payload(), 103)
    assert json.loads(first[1])["session_id"] != json.loads(second[1])["session_id"]
    with pytest.raises(ValueError, match="WRONG_SESSION"):
        gateway.dispatch("POST", "/v1/close", first_close, 104)
    assert json.loads(gateway.dispatch("GET", "/v1/status", b"", 105)[1])["status"] == "CONNECTED"


def test_export_has_structured_files_and_never_claims_human_validation():
    gateway = Gateway("x" * 32, "fixture-hash")
    start = json.loads(gateway.dispatch("POST", "/v1/session", start_payload(), 100)[1])
    session = {"session_id": start["session_id"]}
    gateway.dispatch(
        "POST", "/v1/recording", json.dumps({**session, "enabled": True}).encode(), 101
    )
    event = dict(session, kind="START_SCENARIO", scenario="LOW_LIGHT")
    gateway.dispatch("POST", "/v1/event", json.dumps(event).encode(), 102)
    code, payload, mime = gateway.dispatch("GET", "/v1/export", b"", 103)
    assert code == 200 and mime == "application/zip"
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert set(archive.namelist()) == {
            "manifest.json",
            "metrics.json",
            "metrics.csv",
            "events.jsonl",
            "human-review.json",
        }
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["human_validation"] == "NOT_PERFORMED"
        assert manifest["raw_frames_included"] is False
        assert json.loads(archive.read("events.jsonl"))["scenario"] == "LOW_LIGHT"


def test_dropped_phone_can_reconnect_without_reusing_queued_frame_or_old_session():
    gateway = Gateway("x" * 32, "fixture-hash")
    original = json.loads(gateway.dispatch("POST", "/v1/session", start_payload(), 100)[1])
    gateway.pending.put("orphaned capture")
    later = 3_000_000_101
    new = json.loads(gateway.dispatch("POST", "/v1/session", start_payload(), later)[1])
    assert new["session_id"] != original["session_id"]
    assert gateway.pending.take() is None
    close = json.dumps({"session_id": original["session_id"]}).encode()
    with pytest.raises(ValueError, match="WRONG_SESSION"):
        gateway.dispatch("POST", "/v1/close", close, later + 1)


def test_lan_binding_requires_tls_before_socket_open():
    with pytest.raises(ValueError, match="LAN_REQUIRES_TLS"):
        FieldHTTPServer(("0.0.0.0", 0), Gateway("x" * 32, "hash"))


def test_export_compression_does_not_block_gateway_admission(monkeypatch):
    gateway = Gateway("x" * 32, "fixture-hash")
    gateway.dispatch("POST", "/v1/session", start_payload(), 100)
    entered = threading.Event()
    release = threading.Event()

    def slow_export(*_):
        entered.set()
        release.wait(5)
        return b"zip"

    monkeypatch.setattr("perception_lab.field_gateway.export_session", slow_export)
    worker = threading.Thread(target=gateway.dispatch, args=("GET", "/v1/export", b"", 101))
    worker.start()
    try:
        assert entered.wait(3)
        acquired = gateway.lock.acquire(timeout=1)
        assert acquired
        gateway.lock.release()
    finally:
        release.set()
        worker.join(3)
    assert not worker.is_alive()


def test_http_auth_origin_and_body_limit():
    server = FieldHTTPServer(("127.0.0.1", 0), Gateway("x" * 32, "hash"))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}/v1/status"
    try:
        with pytest.raises(urllib.error.HTTPError) as denied:
            urllib.request.urlopen(url, timeout=2)
        assert denied.value.code == 401
        headers = {"Authorization": "Bearer " + "x" * 32}
        with urllib.request.urlopen(
            urllib.request.Request(url, headers=headers), timeout=2
        ) as response:
            assert json.load(response)["status"] == "DISCONNECTED"
            assert response.headers["Cache-Control"] == "no-store"
        with pytest.raises(urllib.error.HTTPError) as origin:
            urllib.request.urlopen(
                urllib.request.Request(
                    url, headers={**headers, "Origin": "https://attacker.example"}
                ),
                timeout=2,
            )
        assert origin.value.code == 403
        with pytest.raises(urllib.error.HTTPError) as oversized:
            urllib.request.urlopen(
                urllib.request.Request(url, data=b"x" * 16385, headers=headers), timeout=2
            )
        assert oversized.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
        assert not worker.is_alive()
