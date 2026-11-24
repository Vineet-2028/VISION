"""Exercise authenticated loopback HTTP and the real isolated Guardian worker."""

import argparse
import io
import json
import secrets
import threading
import urllib.request
import zipfile
from pathlib import Path
from time import monotonic, perf_counter_ns, sleep

from alpha_field_gateway import (
    FieldHTTPServer,
    Gateway,
    WorkerHost,
    hash_file,
    release_profile,
)

from perception_lab.field_protocol import PROTOCOL, FrameHeader, encode_frame


def smoke(manifest, runtime, output):
    import cv2
    import numpy as np

    token = secrets.token_urlsafe(32)
    gateway = Gateway(token, hash_file(manifest))
    host = WorkerHost(gateway, release_profile(manifest), runtime)
    with FieldHTTPServer(("127.0.0.1", 0), gateway) as server:
        port = server.server_port

        def request(path, data=None):
            body = json.dumps(data).encode() if isinstance(data, dict) else data
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/v1/{path}",
                data=body,
                headers={"Authorization": "Bearer " + token},
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.read() if path == "export" else json.load(response)

        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        host.start()
        session_id = None
        try:
            frames = []
            version = 0
            start = request(
                "session",
                {
                    "protocol_version": PROTOCOL,
                    "client_version": "qualification",
                    "device_id": "synthetic-local",
                    "mode": "DESKTOP_REALTIME",
                    "width": 320,
                    "height": 240,
                    "format": "JPEG",
                    "capabilities": ["NO_AUDIO"],
                },
            )
            session_id = start["session_id"]
            request("recording", {"enabled": True, "session_id": session_id})
            request(
                "event", {"kind": "START_SCENARIO", "scenario": "OTHER", "session_id": session_id}
            )
            image = np.random.default_rng(42).integers(0, 255, (240, 320, 3), dtype=np.uint8)
            ok, encoded = cv2.imencode(".jpg", image)
            if not ok:
                raise RuntimeError("JPEG encode failed")
            seq = 0
            until = monotonic() + 75
            last_sync = 0.0
            while monotonic() < until and len(frames) < 3:
                if monotonic() - last_sync > 3:
                    c = request(
                        "sync/start",
                        {"session_id": session_id, "t0": str(perf_counter_ns())},
                    )
                    version = request(
                        "sync/finish",
                        {
                            "session_id": session_id,
                            "challenge": c["challenge"],
                            "t3": str(perf_counter_ns()),
                        },
                    )["version"]
                    last_sync = monotonic()
                now = perf_counter_ns()
                header = FrameHeader(
                    protocol_version=PROTOCOL,
                    session_id=session_id,
                    sequence=seq,
                    camera_ns=str(now),
                    capture_ns=str(now),
                    send_ns=str(perf_counter_ns()),
                    sync_version=version,
                    rotation=0,
                    width=320,
                    height=240,
                    format="JPEG",
                    jpeg_quality=95,
                )
                request("frame", encode_frame(header, encoded.tobytes()))
                sleep(0.1)
                snapshot = request("status")
                if snapshot["worker_status"].startswith("UNAVAILABLE"):
                    raise RuntimeError(snapshot["worker_status"])
                result = snapshot["result"]
                if result and (not frames or result["sequence"] > frames[-1]["sequence"]):
                    phone = request("alerts")
                    if phone["result"] and (
                        "scene" in phone["result"] or "field_alerts" not in phone["result"]
                    ):
                        raise RuntimeError("Phone path returned invalid alert projection")
                    scene = result["scene"]
                    if (
                        scene["source_type"] != "LIVE_CAMERA"
                        or scene["frame"]["source_id"] != session_id
                        or scene["frame"]["sequence"] != result["sequence"]
                        or scene["errors"]
                        or int(result["age_at_response_ns"]) >= 500_000_000
                    ):
                        raise RuntimeError("Incorrect published field result")
                    frames.append(
                        {
                            "sequence": result["sequence"],
                            "age_ns": int(result["age_at_response_ns"]),
                        }
                    )
                seq += 1
            if len(frames) < 3:
                raise RuntimeError("Insufficient fresh engine results: " + str(snapshot["counts"]))
            sleep(0.6)
            if request("status")["result"] is not None or request("alerts")["result"] is not None:
                raise RuntimeError("Stale field scene resurfaced")
            with zipfile.ZipFile(io.BytesIO(request("export"))) as archive:
                audit = json.loads(archive.read("manifest.json"))
                metrics = json.loads(archive.read("metrics.json"))
                review = json.loads(archive.read("human-review.json"))
                latency = metrics["recorded_latency"]
                if (
                    audit["raw_frames_included"]
                    or audit["audio_included"]
                    or not review["items"]
                    or review["human_validation"] != "NOT_PERFORMED"
                ):
                    raise RuntimeError("Invalid recorded field export")
                if "RESULT_PUBLISHED.capture_to_publication_ns" not in latency:
                    raise RuntimeError("Missing capture-to-publication measurements")
            request("close", {"session_id": session_id})
            if request("status")["status"] != "DISCONNECTED":
                raise RuntimeError("Session did not close")
            with output.open("x", encoding="utf-8") as f:
                json.dump(
                    {
                        "status": "PASSED",
                        "fixture": "SYNTHETIC_DESKTOP_LOOPBACK",
                        "frames_sent": seq,
                        "fresh_results": frames,
                        "recorded_latency": latency,
                        "phone_alert_projection_checked": True,
                        "frozen_manifest_sha256": hash_file(manifest),
                        "physical_camera_tested": False,
                        "tts_tested": False,
                    },
                    f,
                    indent=2,
                )
        finally:
            server.shutdown()
            thread.join()
            host.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "manifest",
        "ort-runtime",
        "cuda-libraries",
        "cudnn-directory",
        "output",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    smoke(
        args.manifest,
        [
            args.ort_runtime.resolve(),
            args.cuda_libraries.resolve(),
            args.cudnn_directory.resolve(),
        ],
        args.output,
    )
