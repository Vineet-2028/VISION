import importlib
import io
import json
import struct
import zipfile
from pathlib import Path

import pytest
from PIL import Image


def make_case(tmp_path, session="session", camera="100"):
    def utf(value):
        encoded = value.encode("ascii")
        return struct.pack(">H", len(encoded)) + encoded

    buffer = io.BytesIO()
    Image.new("RGB", (640, 480)).save(buffer, format="JPEG")
    image = buffer.getvalue()
    clip = tmp_path / "clip.bin"
    clip.write_bytes(
        utf("VISION_DIAGNOSTIC_FRAMES_V1")
        + utf("session")
        + struct.pack(">qiqqiiii", 1000, 1, 7, 100, 90, 640, 480, len(image))
        + image
    )
    gateway = tmp_path / "gateway.zip"
    events = [
        {
            "kind": "FRAME_ADMITTED",
            "sequence": 7,
            "camera_ns": camera,
            "host_ns": "900",
            "rotation": 90,
        },
        {
            "kind": "RESULT_PUBLISHED",
            "sequence": 7,
            "alerts": [{"alert_id": "a"}],
            "host_ns": "950",
        },
        {"kind": "TTS_ERROR", "alert_id": "a", "host_ns": "990"},
        {"kind": "TTS_ERROR", "alert_id": "other", "host_ns": "990"},
    ]
    with zipfile.ZipFile(gateway, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"session_id": session}))
        archive.writestr("events.jsonl", "\n".join(json.dumps(e) for e in events))
    return clip, gateway


def importer(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    return importlib.import_module("import_field_case").import_case


def test_import_preserves_exact_bytes_and_links_only_matching_alert(tmp_path, monkeypatch):
    clip, gateway = make_case(tmp_path)
    output = tmp_path / "case"
    importer(monkeypatch)(clip, gateway, output)
    image = (output / "0.jpg").read_bytes()
    assert clip.read_bytes().endswith(image)
    packet = json.loads((output / "0.json").read_text())
    assert packet["correspondence"] == "EXACT_ADMITTED_CAPTURE"
    assert [e["alert_id"] for e in packet["delivery_events"]] == ["a"]
    assert packet["recomputed_output"] is None


@pytest.mark.parametrize("session,camera", [("other", "100"), ("session", "101")])
def test_wrong_session_or_clock_is_rejected_before_output(tmp_path, monkeypatch, session, camera):
    clip, gateway = make_case(tmp_path, session, camera)
    with pytest.raises(ValueError, match="mismatch"):
        importer(monkeypatch)(clip, gateway, tmp_path / "case")
    assert not (tmp_path / "case").exists()


def test_truncated_capture_is_rejected(tmp_path, monkeypatch):
    clip, gateway = make_case(tmp_path)
    clip.write_bytes(clip.read_bytes()[:-1])
    with pytest.raises(ValueError, match="Truncated"):
        importer(monkeypatch)(clip, gateway, tmp_path / "case")


def test_import_retains_later_publication_for_exact_detector_source(tmp_path, monkeypatch):
    clip, gateway = make_case(tmp_path)
    with zipfile.ZipFile(gateway) as archive:
        manifest = archive.read("manifest.json")
        events = archive.read("events.jsonl").decode()
    later = {
        "kind": "RESULT_PUBLISHED",
        "sequence": 9,
        "detector_diagnostics": {
            "source_id": "session",
            "source_sequence": 7,
            "source_observation_ns": "900",
        },
    }
    unrelated = {**later, "detector_diagnostics": {"source_id": "other", "source_sequence": 7}}
    with zipfile.ZipFile(gateway, "w") as archive:
        archive.writestr("manifest.json", manifest)
        archive.writestr(
            "events.jsonl", events + "\n" + json.dumps(later) + "\n" + json.dumps(unrelated)
        )
    output = tmp_path / "case"
    importer(monkeypatch)(clip, gateway, output)
    packet = json.loads((output / "0.json").read_text())
    assert packet["detector_source_events"] == [later]
    assert packet["sequence"] == 7
    assert packet["causal_ledger"]["first_confirmed_failure_stage"] == "UNKNOWN"


def test_import_rejects_different_gateway_orientation_before_writing(tmp_path, monkeypatch):
    clip, gateway = make_case(tmp_path)
    with zipfile.ZipFile(gateway) as archive:
        manifest = archive.read("manifest.json")
        events = archive.read("events.jsonl").decode().splitlines()
    admitted = json.loads(events[0])
    admitted["rotation"] = 180
    events[0] = json.dumps(admitted)
    with zipfile.ZipFile(gateway, "w") as archive:
        archive.writestr("manifest.json", manifest)
        archive.writestr("events.jsonl", "\n".join(events))
    with pytest.raises(ValueError, match="orientation mismatch"):
        importer(monkeypatch)(clip, gateway, tmp_path / "case")
    assert not (tmp_path / "case").exists()


def test_recompute_requires_recorded_release_before_loading_models(tmp_path, monkeypatch):
    clip, gateway = make_case(tmp_path)
    output = tmp_path / "case"
    importer(monkeypatch)(clip, gateway, output)
    replay = importlib.import_module("replay_field_case").replay
    with pytest.raises(ValueError, match="Recorded release identity"):
        replay(output, tmp_path / "replay.json", True)
    assert not (tmp_path / "replay.json").exists()


def test_recomputation_is_separate_from_original_decisions(tmp_path, monkeypatch):
    clip, gateway = make_case(tmp_path)
    output = tmp_path / "case"
    importer(monkeypatch)(clip, gateway, output)
    module = importlib.import_module("replay_field_case")

    def fake_recompute(case, index, frames):
        assert case == output
        assert index["session_id"] == "session"
        frames[0]["recomputed_output"] = {"scope": "TEST_FIXTURE"}
        return {"model_sha256": "fixture"}

    monkeypatch.setattr(module, "recompute_detector", fake_recompute)
    module.replay(output, tmp_path / "replay.json", True)
    result = json.loads((tmp_path / "replay.json").read_text())
    assert result["frames"][0]["recorded_output"][1]["alerts"] == [{"alert_id": "a"}]
    assert result["frames"][0]["recomputed_output"] == {"scope": "TEST_FIXTURE"}
    assert result["full_equivalence"] == "UNAVAILABLE"
    assert json.loads((output / "0.json").read_text())["recomputed_output"] is None


def test_input_replay_preserves_identity_and_rejects_modified_image(tmp_path, monkeypatch):
    clip, gateway = make_case(tmp_path)
    output = tmp_path / "case"
    importer(monkeypatch)(clip, gateway, output)
    replay = importlib.import_module("replay_field_case").replay
    replay(output, tmp_path / "replay.json")
    result = json.loads((tmp_path / "replay.json").read_text())
    assert result["frames"][0]["sequence"] == 7
    assert result["frames"][0]["camera_ns"] == "100"
    assert result["frames"][0]["recomputed_output"] is None
    image = output / "0.jpg"
    image.write_bytes(image.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        replay(output, tmp_path / "tampered.json")
