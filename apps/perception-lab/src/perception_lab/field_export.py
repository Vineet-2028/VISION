"""Portable, bounded structured session export. No image or audio payloads."""

import csv
import io
import json
import zipfile
from collections import defaultdict
from math import ceil

from .field_protocol import PROTOCOL
from .field_state import FieldSession


def export_session(session: FieldSession, now_ns: int) -> bytes:
    with session.lock:
        manifest = {
            "protocol_version": PROTOCOL,
            "session_id": session.session_id,
            "configuration_hash": session.configuration_hash,
            "mode": session.start.mode,
            "raw_frames_included": False,
            "audio_included": False,
            "human_validation": "NOT_PERFORMED",
            "recording_full": session.recording_full,
            "recorded_event_bytes": session.recorded_event_bytes,
        }
        events = tuple(session.events)
        counts = dict(session.counts)
        metrics = {"duration_ns": str(max(0, now_ns - session.started_ns)), "counts": counts}
    csv_buffer = io.StringIO(newline="")
    samples: dict[str, list[int]] = defaultdict(list)
    review_items = []
    for event in events:
        for key in ("capture_to_receive_ns", "capture_to_publication_ns", "capture_to_callback_ns"):
            value = event.get(key)
            if isinstance(value, str) and value.isdecimal():
                samples[f"{event['kind']}.{key}"].append(int(value))
        if event["kind"] == "START_SCENARIO" or event.get("alerts"):
            review_items.append(
                {
                    "host_ns": event["host_ns"],
                    "sequence": event.get("sequence"),
                    "scenario": event.get("scenario"),
                    "alerts": event.get("alerts", []),
                    "review_label": None,
                    "interruption_label": None,
                    "notes": "",
                }
            )
    latency = {}
    for name, values in samples.items():
        values.sort()
        latency[name] = {
            "count": len(values),
            **{f"p{q}_ns": values[ceil(q * len(values) / 100) - 1] for q in (50, 95, 99)},
        }
    metrics["recorded_latency"] = latency
    writer = csv.writer(csv_buffer)
    writer.writerow(["metric", "value"])
    for key, value in sorted(counts.items()):
        writer.writerow([key, value])
    for name, distribution in sorted(latency.items()):
        for key, value in distribution.items():
            writer.writerow([f"{name}.{key}", value])
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
        archive.writestr("events.jsonl", "".join(json.dumps(e) + "\n" for e in events))
        archive.writestr("metrics.json", json.dumps(metrics, indent=2))
        archive.writestr("metrics.csv", csv_buffer.getvalue())
        archive.writestr(
            "human-review.json",
            json.dumps(
                {
                    "session_id": session.session_id,
                    "human_validation": "NOT_PERFORMED",
                    "items": review_items,
                },
                indent=2,
            ),
        )
    return output.getvalue()
