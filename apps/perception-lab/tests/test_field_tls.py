"""Real loopback TLS sockets exercise pairing/replay/rotation without GPU inference."""

import importlib
import json
import ssl
import threading
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

from perception_lab.field_gateway import FieldHTTPServer, Gateway
from perception_lab.field_pairing import PairingAuthority
from perception_lab.field_protocol import PROTOCOL


def test_real_tls_pairing_rotation_wrong_certificate_and_revocation(tmp_path, monkeypatch):
    pytest.importorskip("cryptography")
    pytest.importorskip("qrcode")
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    module = importlib.import_module("wireless_alpha")
    tls, _, _ = module.certificate(tmp_path, "127.0.0.1")
    context = ssl.create_default_context(cafile=str(tmp_path / "cert.pem"))
    authority = PairingAuthority()
    gateway = Gateway("operator-test-" * 4, "fixture-hash")
    with FieldHTTPServer(("127.0.0.1", 0), gateway, tls, authority) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"https://127.0.0.1:{server.server_port}"

        def post(path, data, token=None):
            headers = {"Content-Type": "application/json"}
            if token:
                headers["Authorization"] = "Bearer " + token
            with urlopen(
                Request(origin + path, json.dumps(data).encode(), headers),
                context=context,
                timeout=3,
            ) as response:
                return json.load(response)

        try:
            with pytest.raises(URLError):
                urlopen(origin + "/v1/status", context=ssl.create_default_context(), timeout=3)
            code = authority.issue()
            device = post("/v1/pair", {"code": code})["device_key"]
            with pytest.raises(HTTPError) as reused:
                post("/v1/pair", {"code": code})
            assert reused.value.code == 401
            token = post("/v1/session-token", {"device_key": device})["token"]
            start = {
                "protocol_version": PROTOCOL,
                "client_version": "test",
                "device_id": "fixture",
                "mode": "ANDROID_FIELD_HARNESS",
                "width": 320,
                "height": 240,
                "format": "JPEG",
                "capabilities": ["NO_AUDIO", "CAMERA_REALTIME_CLOCK"],
            }
            session = post("/v1/session", start, token)["session_id"]
            with pytest.raises(HTTPError):
                post("/v1/session", start, token)
            with pytest.raises(HTTPError):
                post("/v1/close", {"session_id": "wrong"}, token)
            next_token = post("/v1/session-token", {"device_key": device})["token"]
            with pytest.raises(HTTPError) as revoked:
                post("/v1/close", {"session_id": session}, token)
            assert revoked.value.code == 401
            assert post("/v1/session", start, next_token)["session_id"] != session
            authority.revoke()
            with pytest.raises(HTTPError):
                post("/v1/session-token", {"device_key": device})
            with pytest.raises(URLError):
                urlopen(
                    f"https://localhost:{server.server_port}/v1/status", context=context, timeout=3
                )
        finally:
            server.shutdown()
            thread.join(3)
