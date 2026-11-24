"""Trust boundary tests: unverified bytes must never become a model asset."""

import hashlib
import io
import json
import runpy
import sys
import urllib.request
from pathlib import Path

import pytest


def setup(tmp_path, monkeypatch, payload=b"verified-model"):
    registry = {
        "schema_version": 1,
        "models": [
            {
                "id": "fixture",
                "filename": "fixture.pt",
                "url": "https://github.com/ultralytics/assets/releases/download/v8.4.0/fixture.pt",
                "sha256": hashlib.sha256(b"verified-model").hexdigest(),
                "bytes": len(b"verified-model"),
            }
        ],
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(registry))
    output = tmp_path / "models"
    monkeypatch.setattr(sys, "argv", ["acquire", "--registry", str(path), "--output", str(output)])

    def response(*args, **kwargs):
        stream = io.BytesIO(payload)
        stream.url = "https://release-assets.githubusercontent.com/fixture"
        return stream

    monkeypatch.setattr(urllib.request, "urlopen", response)
    main = runpy.run_path(str(Path(__file__).resolve().parents[3] / "tools/acquire_v02_models.py"))[
        "main"
    ]
    return main, output


def test_hash_verified_asset_is_activated_and_idempotent(tmp_path, monkeypatch):
    main, output = setup(tmp_path, monkeypatch)
    main()
    assert (output / "fixture.pt").read_bytes() == b"verified-model"
    assert not (output / "fixture.pt.part").exists()
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda *a, **k: pytest.fail("Unexpected download")
    )
    main()


@pytest.mark.parametrize("payload", [b"corrupt--model", b"truncated", b"oversized-model-bytes"])
def test_bad_remote_bytes_never_activate(tmp_path, monkeypatch, payload):
    main, output = setup(tmp_path, monkeypatch, payload)
    with pytest.raises(ValueError):
        main()
    assert not (output / "fixture.pt").exists()


def test_existing_tampered_asset_is_not_overwritten(tmp_path, monkeypatch):
    main, output = setup(tmp_path, monkeypatch)
    output.mkdir()
    (output / "fixture.pt").write_bytes(b"existing")
    with pytest.raises(ValueError, match="Existing model hash mismatch"):
        main()
    assert (output / "fixture.pt").read_bytes() == b"existing"
