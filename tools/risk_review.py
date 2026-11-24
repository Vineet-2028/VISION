"""Prepare or serve a local-only draft event review packet; no automatic ground truth."""

import argparse
import hashlib
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import av

from perception_lab.config import read_json

LABELS = [
    "CLEARLY_RELEVANT_INTERACTION",
    "CLEARLY_IRRELEVANT",
    "AMBIGUOUS",
    "INSUFFICIENT_VISUAL_EVIDENCE",
]
PAGE = """<!doctype html><html lang="en"><meta charset="utf-8">
<title>Sentinel draft interaction review</title>
<style>body{font:18px system-ui;background:#171b24;color:#eee;max-width:1000px;margin:30px auto}
video{width:100%;max-height:65vh}button,select,textarea{font:inherit;margin:8px;padding:8px}
textarea{width:90%}a{color:#9bd}</style>
<h1>Draft interaction review</h1><p>Prototype evidence only. Review the visual interaction,
not collision probability. Machine-selected windows are not ground truth.</p>
<video id="video" src="/video" controls></video><p id="description"></p>
<button id="previous">Previous</button><button id="next">Next</button>
<select id="label"><option value="">Choose a review label</option></select>
<textarea id="notes" aria-label="Review notes"
placeholder="Notes, missing objects, ambiguity"></textarea>
<button id="save">Download review JSON</button><p>No review is uploaded or marked validated.</p>
<script>
let packet,index=0;const video=document.querySelector('#video');
const label=document.querySelector('#label');
const notes=document.querySelector('#notes');
function store(){const w=packet.windows[index];w.review_label=label.value||null;w.notes=notes.value;
w.review_status=label.value?'HUMAN_LABELED_UNADJUDICATED':'DRAFT_REVIEW_REQUIRED';}
function show(){const w=packet.windows[index];video.currentTime=w.start_seconds;
document.querySelector('#description').textContent=`Window ${index+1}/${packet.windows.length}: `+
`${w.start_seconds.toFixed(1)}–${w.end_seconds.toFixed(1)} seconds. ${w.review_status}`;
label.value=w.review_label||'';notes.value=w.notes||'';}
fetch('/manifest.json').then(r=>r.json()).then(p=>{packet=p;
p.labels.forEach(x=>{const o=document.createElement('option');
o.value=x;o.textContent=x;label.append(o)});
show()});
video.addEventListener('timeupdate',()=>{if(packet&&video.currentTime>=packet.windows[index].end_seconds)video.pause()});
document.querySelector('#previous').onclick=()=>{store();index=Math.max(0,index-1);show()};
document.querySelector('#next').onclick=()=>{store();index=Math.min(packet.windows.length-1,index+1);show()};
document.querySelector('#save').onclick=()=>{store();
const blob=new Blob([JSON.stringify(packet,null,2)],{type:'application/json'});
const a=document.createElement('a');a.href=URL.createObjectURL(blob);
a.download='risk-review.json';a.click();
setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
</script></html>"""


def windows(duration, count=30):
    if not 30 <= count <= 60 or duration <= 0:
        raise ValueError("Positive duration and 30–60 windows required")
    length = min(6.0, duration / count)
    return [
        {
            "id": i + 1,
            "start_seconds": i * (duration - length) / (count - 1),
            "end_seconds": i * (duration - length) / (count - 1) + length,
            "review_status": "DRAFT_REVIEW_REQUIRED",
            "review_label": None,
            "notes": "",
            "scenario_tags": [],
        }
        for i in range(count)
    ]


def prepare(config_path, output):
    raw = read_json(config_path)
    video = (config_path.resolve().parent / raw["input"]).resolve(strict=True)
    with av.open(str(video)) as container:
        if container.duration is None:
            raise ValueError("Video duration unavailable")
        duration = min(600.0, container.duration / av.time_base)
    with video.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    packet = {
        "schema_version": 1,
        "dataset": "SENTINEL_FIRST_PERSON_V1",
        "source_path": str(video),
        "source_sha256": digest,
        "selection": (
            "Uniform temporal coverage, not confidence selection; scenario diversity unreviewed"
        ),
        "risk_ground_truth_validated": False,
        "labels": LABELS,
        "windows": windows(duration),
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "manifest.json").write_text(json.dumps(packet, indent=2), encoding="utf-8")
    (output / "index.html").write_text(PAGE, encoding="utf-8")
    return packet


def handler(packet_path):
    packet = json.loads((packet_path / "manifest.json").read_text(encoding="utf-8"))
    video = Path(packet["source_path"]).resolve(strict=True)
    routes = {
        "/": packet_path / "index.html",
        "/manifest.json": packet_path / "manifest.json",
        "/video": video,
    }

    class ReviewHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in routes:
                self.send_error(404)
                return
            path = routes[self.path]
            size = path.stat().st_size
            start, end = 0, size - 1
            range_header = self.headers.get("Range")
            if range_header:
                match = re.fullmatch(r"bytes=(\d+)-(\d*)", range_header)
                if not match:
                    self.send_error(416)
                    return
                start = int(match[1])
                end = min(int(match[2]) if match[2] else end, end)
                if start > end:
                    self.send_error(416)
                    return
            self.send_response(206 if range_header else 200)
            self.send_header(
                "Content-Type",
                "video/mp4"
                if self.path == "/video"
                else "application/json"
                if self.path == "/manifest.json"
                else "text/html; charset=utf-8",
            )
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if range_header:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            try:
                with path.open("rb") as stream:
                    stream.seek(start)
                    remaining = end - start + 1
                    while remaining:
                        block = stream.read(min(65536, remaining))
                        if not block:
                            break
                        self.wfile.write(block)
                        remaining -= len(block)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def log_message(self, *_args):
            pass  # Do not log local paths or review content.

    return ReviewHandler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=8915)
    args = parser.parse_args()
    if args.serve:
        with ThreadingHTTPServer(("127.0.0.1", args.port), handler(args.packet)) as server:
            print(f"Local review: http://127.0.0.1:{args.port}", flush=True)
            server.serve_forever()
    elif args.config:
        prepare(args.config, args.packet)
    else:
        parser.error("Use --config to prepare or --serve to review")


if __name__ == "__main__":
    main()
