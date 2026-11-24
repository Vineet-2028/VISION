import http.client
import importlib
import io
import json
import re
import threading
import zipfile
from pathlib import Path
from urllib.parse import urlencode

from test_field_gateway import start_payload

from perception_lab.field_gateway import Gateway
from perception_lab.field_pairing import PairingAuthority


def test_operator_record_export_and_origin_checks(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    module = importlib.import_module("wireless_alpha")
    gateway = Gateway("x" * 32, "fixture-hash")
    gateway.dispatch("POST", "/v1/session", start_payload(), 100)
    with module.portal(
        PairingAuthority(), "https://fixture", "fixture", "fixture", gateway, 0
    ) as server:
        thread = threading.Thread(target=server.serve_forever)
        thread.start()

        def request(method, body=None, origin="http://127.0.0.1:0"):
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            try:
                connection.request(method, "/", body, {"Host": "127.0.0.1:0", "Origin": origin})
                response = connection.getresponse()
                return response.status, response.read()
            finally:
                connection.close()

        try:
            status, page = request("GET")
            assert status == 200 and b"Diagnostic recording: Stopped" in page
            nonce = re.search(rb'name="nonce" value="([^"]+)"', page).group(1).decode()
            body = urlencode({"nonce": nonce, "action": "record"})
            assert request("POST", body, "https://untrusted.example")[0] == 403
            assert not gateway.session.recording
            assert request("POST", body)[0] == 303
            assert gateway.session.recording
            gateway.session.record("TEST", 101, {"reason": "fixture"})
            status, saved = request("POST", urlencode({"nonce": nonce, "action": "export"}))
            assert status == 200
            with zipfile.ZipFile(io.BytesIO(saved)) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                assert manifest["session_id"] == gateway.session.session_id
                assert manifest["recorded_event_bytes"] > 0
            assert (
                request("POST", urlencode({"nonce": nonce, "action": "stop-recording"}))[0] == 303
            )
            assert not gateway.session.recording
        finally:
            server.shutdown()
            thread.join(timeout=3)
            assert not thread.is_alive()
