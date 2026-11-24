"""Build a separate read-only draft language review; never change earlier labels."""

import argparse
import json
from http.server import ThreadingHTTPServer
from pathlib import Path

from risk_review import PAGE, handler

QUESTIONS = [
    "Was it understandable?",
    "Too long?",
    "Too vague?",
    "Useful direction?",
    "Too urgent?",
    "Would you prefer silence?",
]


def prepare(source, timeline, output):
    packet = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    packet.update(
        mode="OFFLINE REPLAY",
        alert_language_validated_with_users=False,
        language_review_questions=QUESTIONS,
    )
    for window in packet["windows"]:
        window.update(
            alert_timeline=[],
            review_status="DRAFT_REVIEW_REQUIRED",
            review_label=None,
            notes="",
            language_feedback={q: None for q in QUESTIONS},
        )
    with timeline.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            seconds = row["state_timestamp"] / 1e9
            for window in packet["windows"]:
                if window["start_seconds"] <= seconds < window["end_seconds"]:
                    window["alert_timeline"].append(row)
                    break
    if any(not w["alert_timeline"] for w in packet["windows"]):
        raise ValueError("Every window must include alert diagnostics")
    output.mkdir(parents=True, exist_ok=False)
    (output / "manifest.json").write_text(json.dumps(packet, indent=2), encoding="utf-8")
    page = PAGE.replace("interaction review", "OFFLINE REPLAY alert language review")
    page = (
        page.replace("risk-review.json", "alert-review.json")
        .replace(
            '<p id="description"></p>',
            '<p id="description"></p><p>PROTOTYPE / OFFLINE REPLAY / NO AUDIO.</p>'
            "<p>Notes: clear? long? vague? direction useful? urgent? prefer silence?</p>"
            '<pre id="alerts" style="white-space:pre-wrap;max-height:35vh;overflow:auto"></pre>',
        )
        .replace(
            "label.value=w.review_label",
            "document.querySelector('#alerts').textContent=JSON.stringify(w.alert_timeline,null,2);"
            "label.value=w.review_label",
        )
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
        # Match the existing local reviewer allowlist and source path resolution.
        server = ThreadingHTTPServer(("127.0.0.1", 8917), handler(args.packet))
        try:
            print("OFFLINE REPLAY review: http://127.0.0.1:8917", flush=True)
            server.serve_forever()
        finally:
            server.server_close()
    else:
        prepare(args.source, args.timeline, args.packet)


if __name__ == "__main__":
    main()
