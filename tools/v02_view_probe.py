"""Offline full-file view-diagnostics probe. No object inference or human labels."""

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from time import perf_counter_ns

import numpy as np

from perception_lab.camera_view_quality import (
    CameraViewQualityEstimator,
    ViewQualityConfig,
)
from perception_lab.contracts import SourceIssue
from perception_lab.sources import VideoFileSource


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--interval-ms", type=int, default=1000)
    args = parser.parse_args()
    if not 100 <= args.interval_ms <= 10000:
        parser.error("Interval must be between 100 and 10000 ms")
    args.output.mkdir(parents=True, exist_ok=False)
    with args.video.open("rb") as stream:
        video_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    config = ViewQualityConfig()
    estimator = CameraViewQualityEstimator(config)
    source = VideoFileSource(args.video, "v02-view-probe", max_pixels=4096 * 4096)
    next_ns = 0
    source.realtime_minimum_ns = lambda: next_ns
    counts: Counter[str] = Counter()
    issues: Counter[str] = Counter()
    # Fixed histogram, independent of video length; one-microsecond bins up to 100 ms.
    latency_histogram = np.zeros(100001, dtype=np.int64)
    overflow = 0
    total_ns = 0
    first_ns = None
    last_ns = None
    started = perf_counter_ns()
    complete = False
    try:
        with (args.output / "frames.jsonl").open("x", encoding="utf-8") as sink:
            for item in source:
                if isinstance(item, SourceIssue):
                    issues[item.reason.value] += 1
                    continue
                t0 = perf_counter_ns()
                result = estimator.estimate(item)
                elapsed = perf_counter_ns() - t0
                total_ns += elapsed
                microseconds = elapsed // 1000
                overflow += int(microseconds > 100000)
                latency_histogram[min(100000, microseconds)] += 1
                counts[result.status.value] += 1
                first_ns = item.identity.observation_ns if first_ns is None else first_ns
                last_ns = item.identity.observation_ns
                next_ns = last_ns + args.interval_ms * 1_000_000
                sink.write(
                    json.dumps({**asdict(result), "diagnostics_duration_ns": elapsed}) + "\n"
                )
        complete = True
    finally:
        source.close()
        count = sum(counts.values())
        cumulative = np.cumsum(latency_histogram)
        quantiles = {
            str(p): int(np.searchsorted(cumulative, max(1, int(np.ceil(count * p))))) / 1000
            if count
            else None
            for p in (0.5, 0.95, 0.99)
        }
        report = {
            "schema_version": 1,
            "scope": "VIEW_DIAGNOSTICS_ONLY_NOT_FULL_PERCEPTION_PIPELINE",
            "status": "COMPLETE" if complete else "INCOMPLETE",
            "video_sha256": video_hash,
            "configuration": config.model_dump(),
            "configuration_sha256": estimator.configuration_hash,
            "sampling_interval_ms": args.interval_ms,
            "frames_evaluated": count,
            "frames_skipped_conversion": source.skipped_conversion,
            "source_issues": dict(issues),
            "first_sample_ns": first_ns,
            "last_sample_ns": last_ns,
            "status_counts": dict(counts),
            "diagnostic_mean_ms": total_ns / count / 1e6 if count else None,
            "diagnostic_quantile_ms_1us_histogram": quantiles,
            "latencies_over_100ms": overflow,
            "wall_seconds": (perf_counter_ns() - started) / 1e9,
            "human_quality_labels": False,
            "accuracy_measured": False,
            "production_safety_validated": False,
        }
        (args.output / "summary.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(report, indent=2))
    if issues or not count:
        raise SystemExit("Probe has missing/invalid source observations; inspect summary")


if __name__ == "__main__":
    main()
