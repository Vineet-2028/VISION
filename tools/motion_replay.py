"""Bounded offline motion replay, sampling source PTS before expensive RGB conversion."""

import argparse
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

import av
import psutil

from perception_lab.config import Calibration, PreprocessConfig, read_json
from perception_lab.contracts import Frame, FrameIdentity, PixelFormat, TimingProvenance
from perception_lab.ego_runtime import VisualEgoEstimator
from perception_lab.flow import DenseFlowField
from perception_lab.flow_runtime import FlowAdapter
from perception_lab.geometry import CoreGeometry
from perception_lab.metrics import Distribution
from perception_lab.motion_config import MotionConfig
from perception_lab.motion_geometry import calibration_hash, compensate
from perception_lab.preprocessing import BasicPreprocessor
from perception_lab.sources import pts_to_ns


def replay(source, calibration, output, seconds, interval_ms):
    if output.exists():
        raise ValueError("Output exists")
    if not source.is_file() or source.suffix.lower() not in {".mp4", ".mkv", ".mov"}:
        raise ValueError("Local self-contained video required")
    config = MotionConfig(
        max_gap_ns=min(5_000_000_000, interval_ms * 2_000_000), ransac_iterations=100
    )
    geometry = CoreGeometry(Calibration.model_validate(read_json(calibration)))
    adapter = FlowAdapter(config, "offline-motion-session", calibration_hash(geometry))
    estimator = VisualEgoEstimator(geometry, config)
    pre = BasicPreprocessor(geometry, PreprocessConfig())
    process = psutil.Process()
    start_rss = peak = process.memory_info().rss
    distributions = {
        name: Distribution(2048) for name in ("flow", "ego", "compensation", "processing_age")
    }
    states = Counter()
    counts = Counter(decoded=0, sampled=0, skipped_before_conversion=0, pairs=0, motion_available=0)
    started = time.perf_counter_ns()
    next_ns = 0
    last_ns = None
    memory_samples = []
    # Open a local handle, not a URL; same protocol/demux restrictions as Task005.
    try:
        with (
            source.open("rb") as handle,
            av.open(
                handle,
                options={"format_whitelist": "mov,matroska,webm", "protocol_whitelist": "file"},
            ) as container,
        ):
            stream = container.streams.video[0]
            stream.codec_context.thread_count = 1
            for sequence, native in enumerate(container.decode(video=0)):
                ns = pts_to_ns(native.pts, native.time_base)
                if ns is None:
                    raise ValueError("Missing source PTS")
                if ns >= seconds * 1_000_000_000:
                    break
                counts["decoded"] += 1
                last_ns = ns
                if ns < next_ns:
                    counts["skipped_before_conversion"] += 1
                    continue
                next_ns = ns + interval_ms * 1_000_000
                if native.width * native.height > 8_294_400:
                    raise ValueError("Image exceeds decode bound")
                start = time.perf_counter_ns()
                identity = FrameIdentity(
                    "source-pts", sequence, ns, TimingProvenance.AUTHORITATIVE_PTS
                )
                pixels = native.to_ndarray(format="rgb24")
                image = pre.prepare(
                    Frame(identity, pixels, PixelFormat.RGB, start, time.perf_counter_ns())
                )
                flow_start = time.perf_counter_ns()
                flow = adapter.flow(image, identity)
                distributions["flow"].add(time.perf_counter_ns() - flow_start)
                counts["sampled"] += 1
                if flow is not None:
                    counts["pairs"] += 1
                    sparse = (
                        flow.sparse(config.max_features)
                        if isinstance(flow, DenseFlowField)
                        else flow
                    )
                    ego_start = time.perf_counter_ns()
                    motion = estimator.estimate(sparse)
                    distributions["ego"].add(time.perf_counter_ns() - ego_start)
                    states[motion.quality.reason] += 1
                    compensation_start = time.perf_counter_ns()
                    residual = compensate(geometry, sparse, motion)
                    distributions["compensation"].add(time.perf_counter_ns() - compensation_start)
                    counts["motion_available"] += int(residual is not None)
                distributions["processing_age"].add(time.perf_counter_ns() - start)
                rss = process.memory_info().rss
                peak = max(peak, rss)
                # Fixed maximum 121 samples at 5s source intervals, not a growing timeline.
                if len(memory_samples) < 121 and ns >= len(memory_samples) * 5_000_000_000:
                    memory_samples.append(rss)
    finally:
        adapter.close()
    if counts["pairs"] == 0 or last_ns is None or last_ns < (seconds - 1) * 1_000_000_000:
        raise ValueError("Insufficient motion pairs/source coverage")
    with source.open("rb") as handle:
        source_hash = hashlib.file_digest(handle, "sha256").hexdigest()
    report = {
        "schema_version": 1,
        "mode": "OFFLINE_SAMPLED_PTS",
        "source_sha256": source_hash,
        "source_end_ns": last_ns,
        "requested_seconds": seconds,
        "sample_interval_ms": interval_ms,
        "configuration": config.model_dump(),
        "counts": dict(counts),
        "states": dict(states),
        "queue_depth": 0,
        "wall_seconds": (time.perf_counter_ns() - started) / 1e9,
        "timing": {name: value.summary() for name, value in distributions.items()},
        "memory": {
            "warmed_start_rss": start_rss,
            "peak_sampled_rss": peak,
            "end_rss": process.memory_info().rss,
            "samples_5s_source": memory_samples,
        },
        "result_age_semantics": (
            "processing age only; offline replay has no wall-clock freshness claim"
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=int, choices=range(1, 601), default=600)
    parser.add_argument("--interval-ms", type=int, choices=(100, 200, 500, 1000), default=500)
    args = parser.parse_args()
    replay(args.input, args.calibration, args.output, args.seconds, args.interval_ms)
