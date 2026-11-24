"""Deterministic, offline inspection of explicitly saved field exports."""

import argparse
import csv
import html
import io
import json
import zipfile
from pathlib import Path

MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_EVENTS = 10_000


def report(source: Path, output: Path) -> None:
    if source.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("Export exceeds input limit")
    with zipfile.ZipFile(source) as archive:
        names = archive.namelist()
        if names.count("manifest.json") != 1 or names.count("events.jsonl") != 1:
            raise ValueError("Missing or duplicate export members")
        for name in ("manifest.json", "events.jsonl"):
            if archive.getinfo(name).file_size > MAX_INPUT_BYTES:
                raise ValueError("Expanded export exceeds input limit")
        manifest = json.loads(archive.read("manifest.json"))
        lines = archive.read("events.jsonl").decode("utf-8").splitlines()
    if len(lines) > MAX_EVENTS:
        raise ValueError("Too many diagnostic events")
    session = manifest.get("session_id")
    if not isinstance(session, str) or not session:
        raise ValueError("Missing session identity")
    rows = []
    for index, line in enumerate(lines):
        event = json.loads(line)
        if not isinstance(event, dict):
            raise TypeError("Invalid event")
        if event.get("session_id", session) != session:
            raise ValueError("Mixed sessions")
        stamp = event.get("host_ns")
        if not isinstance(stamp, str) or not stamp.isdecimal():
            raise ValueError("Missing host clock provenance")
        diagnostics = event.get("diagnostics")
        stage_evidence = "NOT_RECORDED"
        if diagnostics is not None:
            if (
                not isinstance(diagnostics, dict)
                or diagnostics.get("schema") != "vision.field.stage-ledger.v1"
                or diagnostics.get("session_id") != session
                or diagnostics.get("sequence") != event.get("sequence")
            ):
                raise ValueError("Diagnostic lineage mismatch")
            stages = diagnostics.get("stages")
            if not isinstance(stages, list) or len(stages) > 16:
                raise ValueError("Invalid stage ledger")
            stage_evidence = json.dumps(stages, sort_keys=True, ensure_ascii=True)
            if len(stage_evidence) > 4096:
                raise ValueError("Oversized stage ledger")
        rows.append(
            {
                "event_index": index,
                "session_id": session,
                "host_ns": stamp,
                "clock_domain": "EXPORT_HOST_MONOTONIC",
                "kind": str(event.get("kind", "UNKNOWN")),
                "sequence": event.get("sequence"),
                "first_proven_loss_reason": "UNKNOWN",
                "review_status": "NOT_INDEPENDENTLY_REVIEWED",
                "stage_evidence": stage_evidence,
            }
        )
    result = {
        "schema": "vision.field.failure-report.v1",
        "candidate": "ALPHA_V1_1_DIAGNOSTICS",
        "session_id": session,
        "events": rows,
        "evidence_limit": (
            "Legacy exports omit intermediate causal decisions. Event absence is not proof of loss."
        ),
        "field_accuracy": None,
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    columns = [
        "event_index",
        "session_id",
        "host_ns",
        "clock_domain",
        "kind",
        "sequence",
        "first_proven_loss_reason",
        "review_status",
        "stage_evidence",
    ]
    csv_text = io.StringIO(newline="")
    writer = csv.DictWriter(csv_text, fieldnames=columns)
    writer.writeheader()
    # Prevent spreadsheet formula execution from imported string fields.
    writer.writerows(
        {
            key: "'" + value
            if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r"))
            else value
            for key, value in row.items()
        }
        for row in rows
    )
    (output / "report.csv").write_text(csv_text.getvalue(), encoding="utf-8")
    table = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(row[key]))}</td>" for key in columns) + "</tr>"
        for row in rows
    )
    (output / "report.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>VISION field evidence</title>'
        "<h1>VISION field evidence</h1><p>"
        + html.escape(result["evidence_limit"])
        + "</p><table><thead><tr>"
        + "".join(f"<th>{key}</th>" for key in columns)
        + "</tr></thead><tbody>"
        + table
        + "</tbody></table></html>",
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report(args.export, args.output)
