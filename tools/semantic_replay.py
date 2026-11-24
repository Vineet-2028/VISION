"""Bounded source-PTS sampled semantic replay. Offline age is not real-time freshness."""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter_ns

import av
import psutil

from perception_lab.config import Calibration, PreprocessConfig, read_json
from perception_lab.contracts import Frame, FrameIdentity, PixelFormat, TimingProvenance
from perception_lab.geometry import CoreGeometry
from perception_lab.metrics import Distribution
from perception_lab.preprocessing import BasicPreprocessor
from perception_lab.semantic_config import SemanticConfig
from perception_lab.semantic_runtime import OnnxSemanticSegmenter
from perception_lab.sources import pts_to_ns
from perception_lab.surfaces import SurfaceEvidenceExtractor


def replay(source, calibration, profiles, provider, output, seconds, hz):
    if (
        output.exists()
        or not source.is_file()
        or source.suffix.lower() not in {".mp4", ".mov", ".mkv"}
    ):
        raise ValueError("Local video and new output required")
    geometry = CoreGeometry(Calibration.model_validate(read_json(calibration)))
    pre = BasicPreprocessor(geometry, PreprocessConfig())
    model = OnnxSemanticSegmenter(
        SemanticConfig.model_validate(read_json(profiles)[provider]),
        profiles.parent,
        "semantic-replay",
    )
    extractor = SurfaceEvidenceExtractor()
    process = psutil.Process()
    start_rss = peak = process.memory_info().rss
    metrics = {name: Distribution(2048) for name in ("semantic", "surface", "processing_age")}
    decoded = skipped = updates = 0
    next_ns, previous_ns = 0, -1
    started = perf_counter_ns()
    samples = []
    with (
        source.open("rb") as handle,
        av.open(
            handle, options={"format_whitelist": "mov,matroska,webm", "protocol_whitelist": "file"}
        ) as container,
    ):
        container.streams.video[0].codec_context.thread_count = 1
        for sequence, native in enumerate(container.decode(video=0)):
            ns = pts_to_ns(native.pts, native.time_base)
            if ns is None or ns <= previous_ns or native.is_corrupt:
                raise ValueError("Invalid observation")
            if ns >= seconds * 1_000_000_000:
                break
            previous_ns = ns
            decoded += 1
            if ns < next_ns:
                skipped += 1
                continue
            next_ns = ns + 1_000_000_000 // hz
            if native.width * native.height > 8_294_400:
                raise ValueError("Oversized source")
            start = perf_counter_ns()
            identity = FrameIdentity("source-pts", sequence, ns, TimingProvenance.AUTHORITATIVE_PTS)
            pixels = native.to_ndarray(format="rgb24")
            image = pre.prepare(Frame(identity, pixels, PixelFormat.RGB, start, perf_counter_ns()))
            semantic_start = perf_counter_ns()
            semantic = model.segment(image, identity)
            surface_start = perf_counter_ns()
            surface = extractor.extract(semantic)
            end = perf_counter_ns()
            metrics["semantic"].add(surface_start - semantic_start)
            metrics["surface"].add(end - surface_start)
            metrics["processing_age"].add(end - start)
            updates += 1
            peak = max(peak, process.memory_info().rss)
            if len(samples) < 121 and ns >= len(samples) * 5_000_000_000:
                samples.append(process.memory_info().rss)
            del surface, semantic
            if updates % 30 == 0:
                print(f"Source seconds={ns / 1e9:.1f}; updates={updates}", flush=True)
    if not updates or previous_ns < (seconds - 1) * 1_000_000_000:
        raise ValueError("Insufficient replay coverage")
    with source.open("rb") as handle:
        source_hash = hashlib.file_digest(handle, "sha256").hexdigest()
    report = {
        "mode": "OFFLINE_SAMPLED_PTS",
        "source_sha256": source_hash,
        "source_end_ns": previous_ns,
        "requested_hz": hz,
        "updates": updates,
        "decoded": decoded,
        "skipped_before_conversion": skipped,
        "queue_depth": 0,
        "failures": 0,
        "wall_seconds": (perf_counter_ns() - started) / 1e9,
        "timing": {k: v.summary() for k, v in metrics.items()},
        "memory": {
            "start_rss": start_rss,
            "peak_sampled_rss": peak,
            "end_rss": process.memory_info().rss,
            "samples": samples,
        },
        "provenance": model.provenance.__dict__,
        "freshness": "processing age only; no real-time qualification",
    }
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "calibration", "profiles", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--seconds", type=int, choices=range(1, 601), default=600)
    parser.add_argument("--hz", type=int, choices=(1, 2, 5), default=1)
    a = parser.parse_args()
    replay(a.source, a.calibration, a.profiles, a.provider, a.output, a.seconds, a.hz)
