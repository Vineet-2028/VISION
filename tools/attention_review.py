"""Extend the existing local read-only reviewer with draft attention evidence."""

import argparse
import json
from collections import Counter
from http.server import ThreadingHTTPServer
from pathlib import Path

from risk_review import PAGE, handler

LABELS = [
    "SHOULD_INTERRUPT_NOW",
    "SHOULD_REMAIN_SILENT",
    "AMBIGUOUS",
    "INSUFFICIENT_CONTEXT",
    "TOO_EARLY",
    "TOO_LATE",
    "REPEAT_UNNECESSARY",
]


def compact(output):
    """Keep the browser packet small; full per-entity evidence stays in local JSONL."""
    return {
        "state_timestamp": output["state_timestamp"],
        "scene_status": output["scene_status"],
        "selected": [
            {
                key: d[key]
                for key in (
                    "entity_id",
                    "decision",
                    "priority",
                    "source_risk_level",
                    "source_risk_quality",
                    "reason_codes",
                    "novelty",
                    "event",
                    "interaction_reasons",
                )
            }
            for d in output["selected"]
        ],
        "suppression_counts": dict(Counter(s["reason"] for s in output["suppressed"])),
        "suppressed_entities": len(output["suppressed"]),
    }


def prepare(source, timeline, output):
    packet = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    packet.update(
        labels=LABELS,
        attention_policy_validated_with_humans=False,
        alert_usefulness_validated=False,
    )
    for window in packet["windows"]:
        window.update(
            review_status="DRAFT_REVIEW_REQUIRED",
            review_label=None,
            notes="",
            attention_timeline=[],
        )
    with timeline.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            seconds = row["NOVELTY_ESCALATION"]["state_timestamp"] / 1e9
            for window in packet["windows"]:
                if window["start_seconds"] <= seconds < window["end_seconds"]:
                    window["attention_timeline"].append({p: compact(o) for p, o in row.items()})
                    break
    if any(not w["attention_timeline"] for w in packet["windows"]):
        raise ValueError("Every draft review window must contain evaluated attention")
    output.mkdir(parents=True, exist_ok=False)
    (output / "manifest.json").write_text(json.dumps(packet, indent=2), encoding="utf-8")
    page = (
        PAGE.replace("interaction review", "attention review")
        .replace("risk-review.json", "attention-review.json")
        .replace(
            '<p id="description"></p>',
            '<p id="description"></p><pre id="timeline"></pre>',
        )
    )
    page = page.replace(
        "</style>",
        "pre{white-space:pre-wrap;max-height:32vh;overflow:auto;font-size:13px}</style>",
    )
    page = page.replace(
        "label.value=w.review_label",
        "document.querySelector('#timeline').textContent="
        "JSON.stringify(w.attention_timeline,null,2);label.value=w.review_label",
    )
    (output / "index.html").write_text(page, encoding="utf-8")
    return packet


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path)
    parser.add_argument("--timeline", type=Path)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()
    if args.serve:
        with ThreadingHTTPServer(("127.0.0.1", 8916), handler(args.packet)) as server:
            print("Draft attention review: http://127.0.0.1:8916", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
    else:
        prepare(args.source, args.timeline, args.packet)


if __name__ == "__main__":
    main()
