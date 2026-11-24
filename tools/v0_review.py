"""Blind timestamp-stratified review: never selects using pipeline outputs."""

import argparse
import hashlib
import json
import random
from http.server import ThreadingHTTPServer
from pathlib import Path

from risk_review import LABELS, PAGE, handler


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare(source, output, duration=600, count=30, seed=18001):
    if not 30 <= count <= 60 or duration < count * 6:
        raise ValueError("Require 30-60 nonoverlapping six-second source windows")
    rng = random.Random(seed)
    width = duration / count
    windows = []
    for index in range(count):
        start = index * width + rng.uniform(0, width - 6)
        windows.append(
            {
                "id": f"blind-{index + 1:03}",
                "start_seconds": start,
                "end_seconds": start + 6,
                "review_status": "DRAFT_REVIEW_REQUIRED",
                "review_label": None,
                "notes": "",
                "scenario_tags": [],
                "scenario_status": "UNKNOWN_PENDING_HUMAN_REVIEW",
            }
        )
    packet = {
        "schema_version": 1,
        "source_path": str(source.resolve(strict=True)),
        "source_sha256": digest(source),
        "labels": LABELS,
        "windows": windows,
        "selection": "One seeded uniform timestamp in each equal time stratum; no model output",
        "seed": seed,
        "human_review_complete": False,
        "scenario_diversity": "Unestablished; one recording cannot establish deployment diversity",
        "scope": "Window relevance only; not object identity, hazard recall or physical validation",
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "manifest.json").write_text(json.dumps(packet, indent=2), encoding="utf-8")
    page = PAGE.replace("Draft interaction review", "Blind V0 source-window review")
    page = page.replace("risk-review.json", "v0-blind-review.json")
    page = page.replace(
        "Machine-selected windows are not ground truth.",
        "Timestamp-selected windows contain no model overlays. Labels require independent review.",
    )
    (output / "index.html").write_text(page, encoding="utf-8")
    return packet


def examples(source, analysis, output):
    """Separate illustrative packet; never feeds headline reference selection."""
    report = json.loads(analysis.read_text(encoding="utf-8"))
    windows = []
    for kind, entries in report["examples"].items():
        for index, entry in enumerate(entries):
            start = max(0, min(594, entry["source_ns"] / 1e9 - 1))
            windows.append(
                {
                    "id": f"{kind}-{index + 1}",
                    "start_seconds": start,
                    "end_seconds": start + 6,
                    "review_status": "ENGINEERING_EXAMPLE_NOT_GROUND_TRUTH",
                    "review_label": None,
                    "notes": entry["criterion"],
                    "criterion": entry["criterion"],
                    "diagnostics": entry.get("diagnostics"),
                }
            )
    packet = {
        "schema_version": 1,
        "source_path": str(source.resolve(strict=True)),
        "source_sha256": digest(source),
        "labels": LABELS,
        "windows": windows,
        "scope": "Illustrative offline engineering examples; not headline sampling",
        "success_definition": "Text sink acceptance, not useful or correct hazard warning",
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "manifest.json").write_text(json.dumps(packet, indent=2), encoding="utf-8")
    page = PAGE.replace("Draft interaction review", "V0 offline engineering examples")
    page = page.replace("risk-review.json", "v0-example-notes.json")
    page = page.replace(
        '<p id="description"></p>',
        '<p id="description"></p><pre id="diagnostics" '
        'style="white-space:pre-wrap;max-height:40vh;overflow:auto"></pre>',
    )
    page = page.replace(
        "label.value=w.review_label",
        "document.querySelector('#diagnostics').textContent="
        "JSON.stringify(w.diagnostics,null,2);label.value=w.review_label",
    )
    page = page.replace(
        "Machine-selected windows are not ground truth.",
        "Examples show text acceptance or silence, not hazard correctness.",
    )
    (output / "index.html").write_text(page, encoding="utf-8")
    return packet


def rescue_review(existing, output):
    """Keep the exact blind windows; add independent, unanswered usefulness labels."""
    packet = json.loads(existing.read_text(encoding="utf-8"))
    if len(packet["windows"]) != 30:
        raise ValueError("Rescue review requires the original 30-window packet")
    if digest(Path(packet["source_path"])) != packet["source_sha256"]:
        raise ValueError("Review source hash mismatch")
    packet["origin_packet_sha256"] = digest(existing)
    packet["labels"] = ["RELEVANT", "IRRELEVANT", "AMBIGUOUS", "INSUFFICIENT_CONTEXT"]
    packet["interruption_labels"] = [
        "SHOULD_INTERRUPT",
        "SHOULD_REMAIN_SILENT",
        "TOO_LATE",
        "REPEAT_UNNECESSARY",
    ]
    packet["human_review_complete"] = False
    packet["scope"] = "Human window relevance and desired interruption; unadjudicated, not safety"
    for window in packet["windows"]:
        window["prior_review_label"] = window.get("review_label")
        window["review_label"] = None
        window["interruption_label"] = None
        window["review_status"] = "DRAFT_REVIEW_REQUIRED"
    page = PAGE.replace("Draft interaction review", "V0 rescue human review")
    page = page.replace("risk-review.json", "v0-rescue-human-review.json")
    page = page.replace(
        '<textarea id="notes"',
        '<select id="interrupt"><option value="">Choose interruption judgement'
        '</option></select><textarea id="notes"',
    )
    page = page.replace(
        "const notes=", "const interrupt=document.querySelector('#interrupt');const notes="
    )
    page = page.replace(
        "w.review_label=label.value||null;",
        "w.review_label=label.value||null;w.interruption_label=interrupt.value||null;",
    )
    page = page.replace(
        "w.review_status=label.value?", "w.review_status=(label.value&&interrupt.value)?"
    )
    page = page.replace(
        "label.value=w.review_label||'';",
        "label.value=w.review_label||'';interrupt.value=w.interruption_label||'';",
    )
    page = page.replace(
        "show()});",
        "p.interruption_labels.forEach(x=>{const o=document.createElement('option');"
        "o.value=x;o.textContent=x;interrupt.append(o)});show()});",
    )
    output.mkdir(parents=True, exist_ok=False)
    (output / "manifest.json").write_text(json.dumps(packet, indent=2), encoding="utf-8")
    (output / "index.html").write_text(page, encoding="utf-8")
    return packet


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--rescue-from", type=Path)
    args = parser.parse_args()
    if args.serve:
        with ThreadingHTTPServer(("127.0.0.1", 8918), handler(args.packet)) as server:
            print("Blind review: http://127.0.0.1:8918", flush=True)
            server.serve_forever()
    elif args.rescue_from:
        rescue_review(args.rescue_from, args.packet)
    elif args.source:
        prepare(args.source, args.packet)
    else:
        parser.error("--source required to prepare packet")
