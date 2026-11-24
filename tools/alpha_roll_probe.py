"""Bounded CPU roll canvas/FOV microbenchmark; not detector or pipeline qualification."""

import argparse
import hashlib
import json
from math import radians
from pathlib import Path
from time import perf_counter_ns

import av
import cv2
import numpy as np
import psutil
from v0_analyze import quantiles

from perception_lab.camera_orientation import CameraOrientationState
from perception_lab.camera_roll import RollCanonicalizer
from perception_lab.config import Calibration
from perception_lab.contracts import Frame, FrameIdentity, PixelFormat, TimingProvenance
from perception_lab.corridor import clip_rect
from perception_lab.geometry import CoreGeometry
from perception_lab.sources import pts_to_ns


def area(points):
    return (
        abs(
            sum(
                a[0] * b[1] - b[0] * a[1]
                for a, b in zip(points, points[1:] + points[:1], strict=True)
            )
        )
        / 2
    )


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Refusing to overwrite evidence")
    config = json.loads(args.config.read_text())
    video = (args.config.parent / config["input"]).resolve()
    calibration_path = (args.config.parent / config["calibration"]).resolve()
    geometry = CoreGeometry(Calibration.model_validate_json(calibration_path.read_text()))
    root = Path(__file__).resolve().parents[1]
    runtime_paths = [
        *sorted((root / "apps/perception-lab/src/perception_lab").glob("*.py")),
        Path(__file__).resolve(),
        root / "packages/guardian-core/target/guardian-core-0.1.0.jar",
    ]
    runtime_hashes = {path.relative_to(root).as_posix(): digest(path) for path in runtime_paths}
    cv2.setNumThreads(1)
    with video.open("rb") as source, av.open(source) as container:
        stream = container.streams.video[0]
        stream.codec_context.thread_count = 1
        native = next(container.decode(stream))
        stamp = pts_to_ns(native.pts, native.time_base)
        if stamp is None or native.is_corrupt:
            raise ValueError("Authoritative source frame unavailable")
        now = perf_counter_ns()
        frame = Frame(
            FrameIdentity(config["source_id"], 0, stamp, TimingProvenance.AUTHORITATIVE_PTS),
            native.to_ndarray(format="rgb24"),
            PixelFormat.RGB,
            now,
            perf_counter_ns(),
        )
    reports = []
    deadline = perf_counter_ns() + 60_000_000_000
    for canvas in ("EXPAND", "PAD", "CROP"):
        canonicalizer = RollCanonicalizer(geometry, canvas)
        for degrees in (-60, -45, -30, -20, -15, -10, 10, 15, 20, 30, 45, 60):
            orientation = CameraOrientationState(
                frame.identity,
                0,
                "GOOD",
                "SYNTHETIC_TEST",
                "explicit-roll-microbenchmark",
                roll_radians=radians(degrees),
            )
            times = []
            for iteration in range(12):
                if psutil.virtual_memory().available < 2 * 1024**3 or perf_counter_ns() >= deadline:
                    raise RuntimeError("Resource/time reserve reached; probe incomplete")
                started = perf_counter_ns()
                result = canonicalizer.canonicalize(frame, orientation)
                elapsed = perf_counter_ns() - started
                if iteration >= 2:
                    times.append(elapsed)
            mapping = result.prepared.mapping
            width, height = mapping.target_dimensions
            corners = tuple(
                mapping.forward(x, y)
                for x, y in (
                    (0, 0),
                    (frame.width, 0),
                    (frame.width, frame.height),
                    (0, frame.height),
                )
            )
            clipped = clip_rect(corners, (0, 0, width, height))
            reports.append(
                {
                    "canvas": canvas,
                    "source_roll_degrees": degrees,
                    "output_width": width,
                    "output_height": height,
                    "geometric_source_fov_retained": area(clipped) / (frame.width * frame.height),
                    "canvas_content_fraction": area(clipped) / (width * height),
                    "warm_call_ns": quantiles(times),
                    "mapping_sha256": mapping.fingerprint,
                }
            )
    with video.open("rb") as source:
        source_hash = hashlib.file_digest(source, "sha256").hexdigest()
    report = {
        "status": "COMPLETE_CPU_ROLL_MICROBENCHMARK",
        "source_sha256": source_hash,
        "source_ns": stamp,
        "runtime_sha256": runtime_hashes,
        "calibration_sha256": digest(calibration_path),
        "source_width": frame.width,
        "source_height": frame.height,
        "opencv": cv2.__version__,
        "numpy": np.__version__,
        "opencv_threads": 1,
        "samples_per_condition": 10,
        "warmup_per_condition": 2,
        "conditions": reports,
        "limitations": [
            "One decoded frame; not full-pipeline or detection measurement",
            "Synthetic roll metadata; no IMU or physical orientation validation",
            "FOV is geometric area; interpolation boundary quality not scored",
            "Concurrent workloads may affect timing",
        ],
    }
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2)
    print(json.dumps({"status": report["status"], "conditions": len(reports)}))


if __name__ == "__main__":
    main()
