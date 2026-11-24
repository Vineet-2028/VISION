"""Summarize paired diagnostic runs without converting software evidence to field truth."""

import argparse
import hashlib
import json
from pathlib import Path

from alpha_realtime_report import summarize


def offline_identity(directory):
    manifest = json.loads((directory / "replay/manifest.json").read_text())
    if manifest["status"] != "COMPLETE":
        raise ValueError("Incomplete offline run")
    digest = hashlib.sha256()
    count = 0
    with (directory / "replay/updates.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            identity = json.loads(line)["identity"]
            if identity["sequence"] != count or identity["observation_ns"] != count * 10**9 // 30:
                raise ValueError("Canonical frame identity mismatch")
            digest.update(f"{count}:{identity['observation_ns']}\n".encode())
            count += 1
    if count != 18000:
        raise ValueError("Canonical 18,000-frame denominator mismatch")
    return {
        "frames": count,
        "identity_sha256": digest.hexdigest(),
        "source_sha256": manifest["source_sha256"],
        "frame_counts": manifest["session"]["summary"]["frame_counts"],
    }


def report(root: Path, candidate_suffix: str = "", realtime_only: bool = False) -> dict:
    realtime = {}
    for arm in ("baseline", "observer", "recording"):
        directory = root / ("realtime-" + arm + (candidate_suffix if arm != "baseline" else ""))
        realtime[arm] = summarize(directory / "replay")
        realtime[arm]["diagnostic_measurements"] = json.loads(
            (directory / "diagnostic-summary.json").read_text()
        )
    baseline = realtime["baseline"]
    screening = {}
    for arm in ("observer", "recording"):
        current = realtime[arm]
        if current["source_sha256"] != baseline["source_sha256"]:
            raise ValueError("Realtime source mismatch")
        # Engineering screen declared before candidate results, not a safety guarantee.
        p95_limit = baseline["whole_run"]["publication_age"]["p95_ns"] * 1.10 + 5_000_000
        screening[arm] = {
            "all_updates_instrumented": current["diagnostic_measurements"].get("generated_updates")
            == current["diagnostic_measurements"]["updates"],
            "p95_within_baseline_plus_10_percent_and_5ms": current["whole_run"]["publication_age"][
                "p95_ns"
            ]
            <= p95_limit,
            "throughput_at_least_90_percent_of_baseline": current["effective_output_fps"]
            >= baseline["effective_output_fps"] * 0.90,
            "no_text_sink_expiry_violations": current["whole_run"]["counts"][
                "delivered_after_expiry"
            ]
            == 0,
            "queue_bounded_to_one": current["peak_queue_depth"] <= 1,
        }
    if realtime_only:
        return {
            "realtime": realtime,
            "engineering_screen": screening,
            "scope": "Realtime engine screen only; offline comparison is a separate artifact",
            "limitations": [
                "Sequential runs have environmental/thermal confounding",
                "Not phone transport, audible delivery or physical accuracy validation",
            ],
        }
    offline = {
        arm: offline_identity(root / ("offline-" + arm)) for arm in ("baseline", "recording")
    }
    if offline["baseline"]["identity_sha256"] != offline["recording"]["identity_sha256"]:
        raise ValueError("Offline source identities differ")
    differing_detections = 0
    with (
        (root / "offline-baseline/replay/updates.jsonl").open(encoding="utf-8") as left,
        (root / "offline-recording/replay/updates.jsonl").open(encoding="utf-8") as right,
    ):
        for a, b in zip(left, right, strict=True):
            a, b = json.loads(a), json.loads(b)
            differing_detections += (a["detector"] or {}).get("detections") != (
                b["detector"] or {}
            ).get("detections")
    return {
        "realtime": realtime,
        "engineering_screen": screening,
        "offline": offline,
        "offline_frames_with_different_detections": differing_detections,
        "limitations": [
            "Single sequential runs; background load and thermal state can differ",
            "Text sink is not phone receipt or audible speech",
            "No independent recall or field correctness measurement",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate-suffix", choices=["", "-v2"], default="")
    parser.add_argument("--realtime-only", action="store_true")
    args = parser.parse_args()
    result = report(args.root, args.candidate_suffix, args.realtime_only)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
