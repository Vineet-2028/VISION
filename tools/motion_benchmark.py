"""Local reviewed-prototype frame-pair diagnostics; no pose/flow ground-truth claim."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from time import perf_counter_ns

import av
import numpy as np

from perception_lab.config import Calibration, PreprocessConfig, read_json
from perception_lab.contracts import Frame, FrameIdentity, PixelFormat, TimingProvenance
from perception_lab.ego_runtime import VisualEgoEstimator
from perception_lab.flow import DenseFlowField
from perception_lab.flow_runtime import FlowAdapter
from perception_lab.geometry import CoreGeometry
from perception_lab.motion_config import MotionConfig
from perception_lab.motion_geometry import calibration_hash, compensate
from perception_lab.preprocessing import BasicPreprocessor


def quantiles(values):
    return {
        f"p{p}": float(np.percentile(values, p)) if values else None for p in (50, 90, 95, 99, 100)
    }


def evaluate(packet_path, calibration_path, output, limit):
    if output.exists():
        raise ValueError("Preserve existing evidence; choose new output")
    packet = read_json(packet_path, max_bytes=20_000_000)
    geometry = CoreGeometry(Calibration.model_validate(read_json(calibration_path)))
    pre = BasicPreprocessor(geometry, PreprocessConfig())
    clips = sorted({f["clip_id"] for f in packet["frames"]})
    reports = []
    for provider in ("lk", "dis"):
        for clip in clips:
            config = MotionConfig(flow_provider=provider, ransac_iterations=100)
            adapter = FlowAdapter(config, "benchmark-" + clip, calibration_hash(geometry))
            estimator = VisualEgoEstimator(geometry, config)
            timings = defaultdict(list)
            states = Counter()
            observations = []
            for sequence, frame in enumerate(
                [f for f in packet["frames"] if f["clip_id"] == clip][: limit + 1]
            ):
                path = (packet_path.parent / frame["path"]).resolve()
                if not path.is_relative_to(packet_path.parent.resolve()):
                    raise ValueError("Frame path escapes dataset")
                if hashlib.sha256(path.read_bytes()).hexdigest() != frame["sha256"]:
                    raise ValueError("Frame hash mismatch")
                with av.open(str(path)) as container:
                    pixels = next(container.decode(video=0)).to_ndarray(format="rgb24")
                identity = FrameIdentity(
                    "benchmark-clock",
                    sequence,
                    frame["observation_ns"],
                    TimingProvenance.AUTHORITATIVE_PTS,
                )
                prepared = pre.prepare(Frame(identity, pixels, PixelFormat.RGB, 0, 1))
                start = perf_counter_ns()
                flow = adapter.flow(prepared, identity)
                timings["flow_total_ms"].append((perf_counter_ns() - start) / 1e6)
                for stage, elapsed in adapter.provider.stage_ns.items():
                    timings[stage + "_ms"].append(elapsed / 1e6)
                if flow is None:
                    continue
                sparse = (
                    flow.sparse(config.max_features) if isinstance(flow, DenseFlowField) else flow
                )
                excluded = np.zeros(len(sparse.valid), dtype=np.bool_)
                x, y = sparse.points_b.T
                for annotation in frame["annotations"]:
                    if annotation["label"] in {"SHELTER", "UNKNOWN"}:
                        continue
                    x1, y1, x2, y2 = annotation["box"]
                    excluded |= (x >= x1) & (x < x2) & (y >= y1) & (y < y2)
                for masked in (False, True):
                    start = perf_counter_ns()
                    motion = estimator.estimate(sparse, excluded if masked else None)
                    timings["ego_ms"].append((perf_counter_ns() - start) / 1e6)
                    states[("masked:" if masked else "unmasked:") + motion.quality.reason] += 1
                    residual = compensate(geometry, sparse, motion)
                    row = {
                        "frame": frame["image_id"],
                        "masked": masked,
                        "features": len(sparse.valid),
                        "valid_fraction": float(sparse.valid.mean()) if len(sparse.valid) else 0,
                        "inlier_ratio": motion.quality.inlier_ratio,
                        "coverage": motion.quality.coverage,
                        "state": motion.quality.reason,
                        "mean_luma": float(pixels.mean()),
                        "raw_median_pixels": float(
                            np.median(np.linalg.norm(sparse.displacement[sparse.valid], axis=1))
                        )
                        if sparse.valid.any()
                        else None,
                    }
                    if residual is not None:
                        for name, mask in (
                            ("excluded", excluded),
                            ("unmasked_candidates", ~excluded),
                        ):
                            valid = residual.valid & mask
                            row[name + "_residual_pixels"] = quantiles(
                                np.linalg.norm(residual.displacement[valid], axis=1).tolist()
                            )
                    observations.append(row)
            adapter.close()
            reports.append(
                {
                    "provider": provider,
                    "clip": clip,
                    "configuration": config.model_dump(),
                    "states": dict(states),
                    "timings": {key: quantiles(values) for key, values in timings.items()},
                    "observations": observations,
                }
            )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_sha256": packet["source_sha256"],
                "scope": "PROTOTYPE_FRAME_PAIRS_NO_POSE_OR_STATIC_DYNAMIC_TRUTH",
                "reports": reports,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--calibration", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=20, choices=range(1, 100))
    args = parser.parse_args()
    evaluate(args.packet, args.calibration, args.output, args.limit)
