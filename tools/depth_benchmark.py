"""Local bounded depth comparison; RGB references are not metric ground truth."""

import argparse
import hashlib
import json
import time
from pathlib import Path

import av
import numpy as np
import psutil

from perception_lab.config import Calibration, PreprocessConfig
from perception_lab.contracts import Frame, FrameIdentity, PixelFormat, TimingProvenance
from perception_lab.depth_config import DepthConfig
from perception_lab.depth_runtime import DepthAnythingProvider
from perception_lab.depth_sampling import SamplingPolicy, sample_region
from perception_lab.detection import Box
from perception_lab.geometry import CoreGeometry
from perception_lab.preprocessing import BasicPreprocessor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument(
        "--adjacent", action="store_true", help="Use first adjacent frames for temporal diagnostics"
    )
    parser.add_argument(
        "--debug-map-limit", type=int, default=0, help="Opt-in maps per model/size, maximum 12"
    )
    args = parser.parse_args()
    if not 1 <= args.limit <= 300:
        parser.error("limit must be 1..300")
    if not 0 <= args.debug_map_limit <= 12:
        parser.error("debug-map-limit must be 0..12")
    packet = json.loads(args.packet.read_text())
    geometry = CoreGeometry(Calibration.model_validate(json.loads(args.calibration.read_text())))
    preprocessor = BasicPreprocessor(geometry, PreprocessConfig())
    frames = packet["frames"][:: max(1, len(packet["frames"]) // args.limit)][: args.limit]
    if args.adjacent:
        frames = packet["frames"][: args.limit]
    runs = []
    process = psutil.Process()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for name, provider in [
        ("Depth-Anything-V2-Small-hf", "dav2_relative"),
        ("Depth-Anything-V2-Metric-Outdoor-Small-hf", "dav2_metric_outdoor"),
    ]:
        directory = args.models / name
        manifest = json.loads((directory / "sentinel-manifest.json").read_text())
        artifacts = manifest["artifacts"]
        for size in (266, 392):
            config = DepthConfig(
                provider=provider,
                weights=str((directory / "model.safetensors").resolve()),
                sha256=artifacts["model.safetensors"]["sha256"],
                config_sha256=artifacts["config.json"]["sha256"],
                processor_sha256=artifacts["preprocessor_config.json"]["sha256"],
                input_size=size,
            )
            model = DepthAnythingProvider(config, Path.cwd())
            samples = []
            for index, metadata in enumerate(frames):
                path = args.packet.parent / metadata["path"]
                if hashlib.sha256(path.read_bytes()).hexdigest() != metadata["sha256"]:
                    raise ValueError("Image hash mismatch")
                with av.open(str(path)) as container:
                    pixels = next(container.decode(video=0)).to_ndarray(format="rgb24")
                identity = FrameIdentity(
                    packet["source_sha256"],
                    index,
                    metadata["observation_ns"],
                    TimingProvenance.AUTHORITATIVE_PTS,
                )
                frame = Frame(identity, pixels, PixelFormat.RGB, 0, 0)
                image = preprocessor.prepare(frame)
                started = time.perf_counter_ns()
                depth = model.estimate_depth(image, identity)
                elapsed = time.perf_counter_ns() - started
                if index < args.debug_map_limit:
                    from PIL import Image

                    valid_values = depth.values[depth.valid]
                    scaled = np.zeros(depth.values.shape, dtype=np.float32)
                    if valid_values.size and float(valid_values.max()) > float(valid_values.min()):
                        scaled = (depth.values - valid_values.min()) / (
                            valid_values.max() - valid_values.min()
                        )
                    if provider == "dav2_metric_outdoor":
                        scaled = 1 - scaled
                    scaled[~depth.valid] = 0
                    prefix = args.output.parent / f"{provider}-{size}-{index}"
                    Image.fromarray(np.uint8(np.clip(scaled, 0, 1) * 255)).save(
                        prefix.with_suffix(".png")
                    )
                    np.savez_compressed(
                        prefix.with_suffix(".npz"), values=depth.values, valid=depth.valid
                    )
                sampling_start = time.perf_counter_ns()
                regions = []
                for annotation in metadata["annotations"][:12]:
                    strategies = {}
                    for strategy in (
                        "central",
                        "eroded",
                        "lower_center",
                        "near_surface",
                        "bottom_patch",
                    ):
                        result = sample_region(
                            depth,
                            Box(*annotation["box"]),
                            SamplingPolicy(strategy=strategy, grid=8),
                        )
                        strategies[strategy] = (
                            None
                            if result is None
                            else {
                                "value": result.value,
                                "mad": result.statistics.mad,
                                "valid_fraction": result.statistics.valid_fraction,
                            }
                        )
                    regions.append(
                        {
                            "label": annotation["label"],
                            "prototype_track_id": annotation["ground_truth_track_id"],
                            "strategies": strategies,
                        }
                    )
                samples.append(
                    {
                        "image_id": metadata["image_id"],
                        "depth": depth.summary(),
                        "latency_ns": elapsed,
                        "timings_ns": dict(model.last_timings_ns),
                        "sampling_ns": time.perf_counter_ns() - sampling_start,
                        "rss": process.memory_info().rss,
                        "regions": regions,
                    }
                )
                print(
                    provider,
                    size,
                    index + 1,
                    "latency_ms",
                    round(elapsed / 1e6, 2),
                    flush=True,
                )
            durations = [s["latency_ns"] / 1e6 for s in samples]
            runs.append(
                {
                    "provider": provider,
                    "input_size": size,
                    "checkpoint": manifest,
                    "latency_ms": dict(
                        zip(
                            ["p50", "p90", "p95", "p99"],
                            np.percentile(durations, [50, 90, 95, 99]).tolist(),
                            strict=True,
                        )
                    ),
                    "rss_peak_sampled": max(s["rss"] for s in samples),
                    "samples": samples,
                }
            )
            args.output.write_text(
                json.dumps(
                    {"status": "PROTOTYPE_NO_METRIC_GROUND_TRUTH", "runs": runs},
                    indent=2,
                    allow_nan=False,
                )
            )
            del model


if __name__ == "__main__":
    main()
