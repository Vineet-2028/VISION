"""Join explicitly exported Android frames and gateway events without guessed matches."""

import argparse
import hashlib
import io
import json
import struct
import zipfile
from pathlib import Path

from perception_lab.field_case_ledger import case_ledger
from perception_lab.field_protocol import check_camera_jpeg


def import_case(clip: Path, gateway: Path, output: Path, feedback: Path | None = None) -> None:
    if clip.stat().st_size > 4 * 1024 * 1024 + 8192 or gateway.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Input too large")
    raw = clip.read_bytes()
    stream = io.BytesIO(raw)

    def read(size: int) -> bytes:
        data = stream.read(size)
        if len(data) != size:
            raise ValueError("Truncated capture")
        return data

    def number(fmt: str) -> int:
        return int(struct.unpack(fmt, read(struct.calcsize(fmt)))[0])

    def text() -> str:
        # Writer uses Java modified UTF; protocol identifiers are ASCII only.
        return read(number(">H")).decode("ascii")

    if text() != "VISION_DIAGNOSTIC_FRAMES_V1":
        raise ValueError("Unknown capture version")
    session = text()
    created_ms = number(">q")
    count = number(">i")
    if not session or not 1 <= count <= 24:
        raise ValueError("Invalid capture manifest")
    frames = []
    last_sequence = last_camera = -1
    for _ in range(count):
        sequence, camera = number(">q"), number(">q")
        rotation, width, height, size = (number(">i") for _ in range(4))
        if (
            sequence <= last_sequence
            or camera <= last_camera
            or rotation not in (0, 90, 180, 270)
            or not 1 <= width <= 1280
            or not 1 <= height <= 1280
            or not 1 <= size <= 512_000
        ):
            raise ValueError("Invalid frame metadata")
        jpeg = read(size)
        check_camera_jpeg(jpeg, width, height)
        frames.append((sequence, camera, rotation, width, height, jpeg))
        last_sequence, last_camera = sequence, camera
    if stream.read(1):
        raise ValueError("Trailing capture bytes")
    if frames[-1][1] - frames[0][1] > 2_000_000_000:
        raise ValueError("Capture exceeds two-second retention window")
    with zipfile.ZipFile(gateway) as archive:
        for name in ("manifest.json", "events.jsonl"):
            if (
                archive.namelist().count(name) != 1
                or archive.getinfo(name).file_size > 16 * 1024 * 1024
            ):
                raise ValueError("Invalid gateway export")
        manifest = json.loads(archive.read("manifest.json"))
        lines = archive.read("events.jsonl").decode().splitlines()
    if manifest.get("session_id") != session or len(lines) > 10_000:
        raise ValueError("Session mismatch or oversized events")
    events = [json.loads(line) for line in lines]
    if any(not isinstance(e, dict) or e.get("session_id", session) != session for e in events):
        raise ValueError("Mixed or malformed events")
    history = []
    if feedback is not None:
        if feedback.stat().st_size > 8 * 1024 * 1024:
            raise ValueError("Oversized feedback")
        exported = json.loads(feedback.read_text(encoding="utf-8"))
        if exported.get("schema") != "vision.history.export.v1":
            raise ValueError("Unknown feedback schema")
        history = exported.get("events")
        if not isinstance(history, list) or len(history) > 1000:
            raise ValueError("Invalid feedback")
        history = [
            e
            for e in history
            if e.get("session_id") == session and e.get("type") == "USER_FEEDBACK"
        ]
    packets = []
    for sequence, camera, rotation, width, height, jpeg in frames:
        selected = [e for e in events if e.get("sequence") == sequence]
        # Async detector work can be published on a later frame. Preserve both
        # identities, never relabel the publication as the detector input.
        source_events = [
            e
            for e in events
            if isinstance(e.get("detector_diagnostics"), dict)
            and e["detector_diagnostics"].get("source_id") == session
            and e["detector_diagnostics"].get("source_sequence") == sequence
            and e not in selected
        ]
        admitted = [e for e in selected if e.get("kind") == "FRAME_ADMITTED"]
        if len(admitted) > 1 or (admitted and admitted[0].get("camera_ns") != str(camera)):
            raise ValueError("Capture correspondence mismatch")
        if admitted and admitted[0].get("rotation") not in (None, rotation):
            raise ValueError("Capture orientation mismatch")
        alerts = [alert for event in selected for alert in event.get("alerts", [])]
        alert_ids = {alert.get("alert_id") for alert in alerts if isinstance(alert, dict)}
        callbacks = [
            e for e in events if e.get("alert_id") is not None and e.get("alert_id") in alert_ids
        ]
        markers = [e for e in history if e.get("details", {}).get("source_sequence") == sequence]
        if any(e["details"].get("source_camera_ns") != str(camera) for e in markers):
            raise ValueError("Feedback capture mismatch")
        packets.append(
            {
                "sequence": sequence,
                "camera_ns": str(camera),
                "rotation": rotation,
                "orientation_correspondence": "EXACT_RECORDED_ROTATION"
                if admitted and admitted[0].get("rotation") == rotation
                else "UNKNOWN",
                "width": width,
                "height": height,
                "jpeg_sha256": hashlib.sha256(jpeg).hexdigest(),
                "correspondence": "EXACT_ADMITTED_CAPTURE"
                if admitted
                else "CORRESPONDENCE_UNKNOWN",
                "recorded_events": selected,
                "detector_source_events": source_events[:16],
                "detector_source_events_omitted": max(0, len(source_events) - 16),
                "delivery_events": callbacks,
                "feedback": markers,
                "recomputed_output": None,
            }
        )
        packets[-1]["causal_ledger"] = case_ledger(packets[-1], session)
        if len(json.dumps(packets[-1]).encode("utf-8")) > 2_000_000:
            raise ValueError("Joined frame evidence exceeds viewer byte budget")
    output.mkdir(parents=True, exist_ok=False)
    generic = {}
    for event in events:
        for alert in event.get("alerts", []):
            if isinstance(alert, dict) and alert.get("semantic_level") == "GENERIC":
                alert_id = alert.get("alert_id")
                if not isinstance(alert_id, str):
                    raise ValueError("Alert identity unavailable")
                generic[alert_id] = {
                    "alert_id": alert_id,
                    "publication_sequence": event.get("sequence"),
                    "first_proven_semantic_loss": "UNKNOWN",
                    "intent_reason_codes": alert.get("reason_codes", []),
                    "object_evidence": event.get("object_diagnostics"),
                    "delivery_events": [e for e in events if e.get("alert_id") == alert_id],
                    "acoustically_heard": "UNVERIFIED",
                }
    (output / "root-causes.json").write_text(
        json.dumps(
            {
                "schema": "vision.field.root-causes.v1",
                "generic_alerts": list(generic.values()),
                "generic_alert_count": len(generic),
                "denominator": "Unique outgoing generic alert IDs in the supplied gateway export",
                "missed_object_causes": None,
                "missed_object_status": "INDEPENDENT_REFERENCE_LABELS_REQUIRED",
                "original_unrecorded_failure": "CANNOT_RECONSTRUCT",
            }
        ),
        encoding="utf-8",
    )
    for index, (frame, packet) in enumerate(zip(frames, packets, strict=True)):
        (output / f"{index}.jpg").write_bytes(frame[-1])
        (output / f"{index}.json").write_text(json.dumps(packet), encoding="utf-8")
    (output / "index.json").write_text(
        json.dumps(
            {
                "schema": "vision.field.case.v1",
                "session_id": session,
                "created_ms": created_ms,
                "frames": [
                    {"index": i, "sequence": p["sequence"], "camera_ns": p["camera_ns"]}
                    for i, p in enumerate(packets)
                ],
                "gateway_manifest": manifest,
                "clip_sha256": hashlib.sha256(raw).hexdigest(),
                "replay_status": "EXACT_CAPTURED_BYTES_AVAILABLE_RECOMPUTATION_NOT_RUN",
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clip", type=Path, required=True)
    parser.add_argument("--gateway", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--feedback", type=Path)
    args = parser.parse_args()
    import_case(args.clip, args.gateway, args.output, args.feedback)
