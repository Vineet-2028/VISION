"""Hash-bound local proposals and diagnostics. Never turns predictions into reviewed truth."""

import argparse
import base64
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from time import perf_counter_ns

import av
import numpy as np
import psutil

from perception_lab.config import Calibration, PreprocessConfig, read_json
from perception_lab.contracts import Frame, FrameIdentity, PixelFormat, TimingProvenance
from perception_lab.geometry import CoreGeometry
from perception_lab.preprocessing import BasicPreprocessor
from perception_lab.semantic_config import SemanticConfig
from perception_lab.semantic_runtime import OnnxSemanticSegmenter
from perception_lab.semantics import TAXONOMY, SemanticClass, restore_labels
from perception_lab.surfaces import SurfaceEvidenceExtractor


def runs(labels):
    flat = labels.ravel()
    edges = np.r_[0, np.flatnonzero(flat[1:] != flat[:-1]) + 1, len(flat)]
    return [[int(flat[a]), int(b - a)] for a, b in zip(edges[:-1], edges[1:], strict=True)]


def prepare(manifest_path, data_root, calibration_path, configurations, output):
    if output.exists():
        raise ValueError("Preserve existing packet; choose a new output directory")
    manifest = read_json(manifest_path, max_bytes=30_000_000)
    selected = []
    for split in ("TRAIN_DEV", "CALIBRATION", "TEST"):
        candidates = sorted(
            [f for f in manifest["images"] if f["split"] == split],
            key=lambda f: f["observation_ns"],
        )
        if len(candidates) < 32:
            raise ValueError("Need at least 32 existing spaced frames per split")
        selected.extend(candidates[int(i)] for i in np.linspace(0, len(candidates) - 1, 32))
    geometry = CoreGeometry(Calibration.model_validate(read_json(calibration_path)))
    pre = BasicPreprocessor(geometry, PreprocessConfig())
    configs = read_json(configurations)
    providers = [
        (
            name,
            OnnxSemanticSegmenter(
                SemanticConfig.model_validate(config), configurations.parent, "semantic-benchmark"
            ),
        )
        for name, config in configs.items()
    ]
    output.mkdir(parents=True)
    (output / "images").mkdir()
    extractor = SurfaceEvidenceExtractor()
    packet = {
        "schema_version": 1,
        "taxonomy": TAXONOMY,
        "dataset": "SENTINEL_FIRST_PERSON_V1",
        "status": "DRAFT_MODEL_ASSISTED",
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "classes": {str(int(c)): c.name for c in SemanticClass},
        "frames": [],
        "selection": "32 evenly spaced existing frames per split; no training",
    }
    timing = defaultdict(list)
    disagreements = []
    process = psutil.Process()
    memory = [process.memory_info().rss]
    for sequence, row in enumerate(selected):
        path = (data_root / row["path"]).resolve()
        if not path.is_relative_to(data_root.resolve()):
            raise ValueError("Frame escapes dataset")
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != row["sha256"]:
            raise ValueError("Frame hash mismatch")
        with av.open(str(path)) as container:
            pixels = next(container.decode(video=0)).to_ndarray(format="rgb24")
        identity = FrameIdentity(
            row["sequence_id"], sequence, row["observation_ns"], TimingProvenance.AUTHORITATIVE_PTS
        )
        prepared = pre.prepare(Frame(identity, pixels, PixelFormat.RGB, 0, 1))
        predictions = {}
        first = None
        for name, provider in providers:
            start = perf_counter_ns()
            semantic = provider.segment(prepared, identity)
            restoration = perf_counter_ns()
            mask = restore_labels(semantic)
            restored = perf_counter_ns()
            surface = extractor.extract(semantic)
            end = perf_counter_ns()
            timing[name + ":total"].append((end - start) / 1e6)
            timing[name + ":restoration"].append((restored - restoration) / 1e6)
            timing[name + ":surface"].append((end - restored) / 1e6)
            for stage, ns in provider.stage_ns.items():
                timing[name + ":" + stage].append(ns / 1e6)
            predictions[name] = runs(mask)
            if first is not None:
                disagreements.append(
                    {
                        "image_id": row["image_id"],
                        "model": name,
                        "agreement_with_first": float((mask == first).mean()),
                    }
                )
            else:
                first = mask
            del surface
        image_name = f"images/{sequence:03d}.jpg"
        (output / image_name).write_bytes(content)
        packet["frames"].append(
            {
                **{
                    k: row[k]
                    for k in (
                        "image_id",
                        "sequence_id",
                        "split",
                        "observation_ns",
                        "sha256",
                        "width",
                        "height",
                        "metadata",
                    )
                },
                "image": image_name,
                "predictions": predictions,
                "review_status": "DRAFT_MODEL_ASSISTED",
                "review_runs": [[255, pixels.shape[0] * pixels.shape[1]]],
            }
        )
        memory.append(process.memory_info().rss)
        print(f"Prepared {sequence + 1}/{len(selected)}", flush=True)
    payload = json.dumps(packet, separators=(",", ":"), allow_nan=False)
    (output / "draft.json").write_text(payload, encoding="utf-8")
    template = Path(__file__).with_name("semantic_review.html").read_text(encoding="utf-8")
    encoded = base64.b64encode(payload.encode()).decode("ascii")
    (output / "review.html").write_text(
        template.replace("__PACKET_BASE64__", encoded), encoding="utf-8"
    )
    report = {
        "status": "DIAGNOSTIC_ONLY_HUMAN_REVIEW_REQUIRED",
        "frames": len(selected),
        "accuracy": None,
        "false_traversable_evidence": None,
        "boundary_accuracy": None,
        "providers": {name: provider.provenance.__dict__ for name, provider in providers},
        "latency_ms": {
            key: {f"p{p}": float(np.percentile(values, p)) for p in (50, 90, 95, 99, 100)}
            for key, values in timing.items()
        },
        "memory_rss": {"start": memory[0], "peak_sampled": max(memory), "end": memory[-1]},
        "disagreement": disagreements,
        "ground_truth_reviewed": False,
    }
    (output / "diagnostics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "data-root", "calibration", "configurations", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    prepare(args.manifest, args.data_root, args.calibration, args.configurations, args.output)
