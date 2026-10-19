"""Opt-in batch-one detector diagnostics on the versioned curated COCO manifest.

No downloads, uploads or model training. JSON parsing is confined to this CLI boundary.
Every candidate uses the same ordered images, minimum confidence, and matching policy.
"""

import argparse
import gc
import importlib
import json
import os
import platform
from dataclasses import asdict, replace
from importlib.metadata import version
from pathlib import Path
from typing import Any, cast

import av
import numpy as np
from numpy.typing import NDArray

from .clocks import processing_ns
from .config import Calibration, PreprocessConfig, canonical_hash, read_json
from .contracts import Frame, FrameIdentity, PixelFormat, TimingProvenance
from .detection import P0_CLASSES, Detection, ObjectClass
from .detection_metrics import GroundTruth, evaluate, iou, localization_error, size_class
from .detector_runtime import UltralyticsDetector, file_hash
from .edge_runtime import PicoDetDetector, YoloXDetector
from .geometry import CoreGeometry
from .metrics import Distribution
from .preprocessing import BasicPreprocessor, PreparedImage
from .robustness import stress_image
from .rtdetr_runtime import RtDetrDetector


def memory_snapshot() -> dict[str, Any]:
    """Process memory, including Python, JVM and runtime; not model-only allocation."""
    try:
        psutil: Any = importlib.import_module("psutil")
    except ImportError:
        return {"available": False}
    info = psutil.Process().memory_info()
    return {
        "available": True,
        "rss_bytes": info.rss,
        "peak_working_set_bytes": getattr(info, "peak_wset", None),
        "scope": "whole process including imports, decode, JVM, cold/warmup and inference",
    }


def runtime_environment() -> dict[str, Any]:
    """Observations, not claims of thermal/power isolation. No process command lines."""
    result: dict[str, Any] = {
        "gc_enabled": gc.isenabled(),
        "thread_environment": {
            key: os.environ.get(key)
            for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")
        },
        "power_thermal_control": "UNCONTROLLED",
        "storage": "OneDrive workspace; media IO excluded, background activity not isolated",
    }
    try:
        psutil: Any = importlib.import_module("psutil")
        result["cpu_affinity"] = psutil.Process().cpu_affinity()
        result["logical_cpu_count"] = psutil.cpu_count()
        result["cpu_frequency_snapshot_mhz"] = psutil.cpu_freq().current
        result["background_process_count"] = len(psutil.pids())
    except (ImportError, AttributeError, OSError):
        result["system_observations"] = "UNAVAILABLE"
    return result


def prepare(
    entry: dict[str, Any], base: Path, sequence: int
) -> tuple[PreparedImage, FrameIdentity]:
    path = (base / entry["path"]).resolve()
    if not path.is_relative_to(base.resolve()) or file_hash(path) != entry["sha256"]:
        raise ValueError("Dataset image path/hash mismatch")
    with av.open(
        str(path),
        options={
            "format_whitelist": "image2,image2pipe,jpeg_pipe,png_pipe,ppm_pipe,bmp_pipe,webp_pipe",
            "protocol_whitelist": "file",
        },
    ) as container:
        decoded = next(container.decode(video=0))
        pixels = cast(NDArray[np.uint8], decoded.to_ndarray(format="rgb24"))
    width, height = entry["width"], entry["height"]
    if pixels.shape != (height, width, 3):
        raise ValueError("Image dimensions mismatch")
    # Identity-only image mapping. These arbitrary intrinsics are NOT camera calibration
    # or depth evidence; only continuous pixel coordinates are evaluated in this command.
    calibration = Calibration.model_validate(
        {
            "schema_version": 1,
            "camera_id": "benchmark",
            "calibration_version": "uncalibrated",
            "camera_frame_id": "benchmark-camera",
            "image_frame_id": "benchmark-image",
            "pixel_convention": "continuous_edges",
            "resolution": {"width": width, "height": height},
            "intrinsics": {"fx": 1.0, "fy": 1.0, "cx": 0.0, "cy": 0.0, "skew": 0},
            "distortion_model": "none",
            "distortion_coefficients": {},
            "calibration_quality": {
                "state": "UNKNOWN",
                "rms_pixels": None,
                "sample_count": None,
                "timestamp_epoch_millis": None,
            },
        }
    )
    identity = (
        FrameIdentity(
            entry["sequence_id"],
            sequence,
            entry["observation_ns"],
            TimingProvenance.AUTHORITATIVE_PTS,
        )
        if "sequence_id" in entry
        else FrameIdentity("coco-stills", sequence, sequence, TimingProvenance.SYNTHETIC)
    )
    frame = Frame(identity, pixels, PixelFormat.RGB, 0, 0)
    return BasicPreprocessor(CoreGeometry(calibration), PreprocessConfig()).prepare(frame), identity


def accuracy(
    dataset: list[dict[str, Any]],
    outputs: list[tuple[Detection, ...]],
    confidence: float,
    overlap: float,
) -> dict[str, Any]:
    from .detection import Box

    tp = fp = fn = 0
    by_class = {label.value: {"tp": 0, "fp": 0, "fn": 0} for label in sorted(P0_CLASSES)}
    sizes = {key: {"matched": 0, "total": 0} for key in ("TINY", "SMALL", "MEDIUM", "LARGE")}
    center_errors, bottom_errors, overlaps, review = [], [], [], []
    localization: dict[str, list[float]] = {
        "PERSON": [],
        "BICYCLE": [],
        "MOTORCYCLE": [],
        "VEHICLE": [],
    }
    slices: dict[str, dict[str, dict[str, int]]] = {
        "scenario": {},
        "lighting": {},
        "motion": {},
        "blur": {},
        "person_density_proxy": {},
    }
    attributes: dict[str, dict[str, dict[str, int]]] = {
        "occlusion": {},
        "visibility": {},
        "truncation": {},
    }
    for entry, predicted in zip(dataset, outputs, strict=True):
        truths = tuple(
            GroundTruth(
                ObjectClass(a["label"]),
                Box(*a["box"]),
                ignore=a["ignore"],
                crowd=a["crowd"],
                occluded=a["occluded"],
                truncated=a["truncated"],
                difficulty=a["difficulty"],
                occlusion_state=a.get("occlusion_state", "UNKNOWN"),
            )
            for a in entry["annotations"]
            if a["label"] in P0_CLASSES
        )
        scoped = tuple(p for p in predicted if p.label in P0_CLASSES)
        result = evaluate(scoped, truths, confidence, overlap)
        tp += result.counts.tp
        fp += result.counts.fp
        fn += result.counts.fn
        for field, groups in slices.items():
            if field == "person_density_proxy":
                people = sum(
                    g.label == ObjectClass.PERSON and not g.ignore and not g.crowd for g in truths
                )
                label = "AT_LEAST_5_ANNOTATED_PEOPLE" if people >= 5 else "UNDER_5_ANNOTATED_PEOPLE"
            else:
                label = str(entry.get(field, "UNKNOWN"))
            slice_count = groups.setdefault(label, {"tp": 0, "fp": 0, "fn": 0, "frames": 0})
            slice_count["frames"] += 1
            for key in ("tp", "fp", "fn"):
                slice_count[key] += getattr(result.counts, key)
        matched = {m.truth for m in result.matches}
        for index, truth in enumerate(truths):
            if truth.ignore or truth.crowd:
                continue
            bucket = sizes[size_class(truth.box, entry["width"], entry["height"])]
            bucket["total"] += 1
            bucket["matched"] += int(index in matched)
            visibility = attributes["visibility"].setdefault(
                truth.occlusion_state, {"matched": 0, "total": 0}
            )
            visibility["total"] += 1
            visibility["matched"] += int(index in matched)
            for field, value in (("occlusion", truth.occluded), ("truncation", truth.truncated)):
                label = "UNKNOWN" if value is None else ("YES" if value else "NO")
                attribute = attributes[field].setdefault(label, {"matched": 0, "total": 0})
                attribute["total"] += 1
                attribute["matched"] += int(index in matched)
        for label in P0_CLASSES:
            count = evaluate(
                tuple(p for p in scoped if p.label == label),
                tuple(g for g in truths if g.label == label),
                confidence,
                overlap,
            ).counts
            for key in ("tp", "fp", "fn"):
                by_class[label.value][key] += getattr(count, key)
        for match in result.matches:
            center, bottom = localization_error(
                scoped[match.prediction].box,
                truths[match.truth].box,
                entry["width"],
                entry["height"],
            )
            center_errors.append(center)
            bottom_errors.append(bottom)
            overlaps.append(match.overlap)
            label = truths[match.truth].label
            group = (
                "VEHICLE"
                if label in {ObjectClass.CAR, ObjectClass.BUS, ObjectClass.TRUCK, ObjectClass.TRAIN}
                else label.value
            )
            if group in localization:
                localization[group].append(bottom)
        low_iou = [
            {
                "prediction": asdict(scoped[m.prediction]),
                "truth": asdict(truths[m.truth]),
                "iou": m.overlap,
            }
            for m in result.matches
            if m.overlap < 0.75
        ]
        fp_context = []
        for pi in result.false_positives:
            prediction = scoped[pi]
            candidates = [
                (iou(prediction.box, g.box), i)
                for i, g in enumerate(truths)
                if not g.ignore and not g.crowd
            ]
            overlap_value, ti = max(candidates, default=(0.0, -1))
            fp_context.append(
                {
                    "prediction": asdict(prediction),
                    "nearest_truth": asdict(truths[ti]) if ti >= 0 else None,
                    "iou": overlap_value,
                    "diagnostic": (
                        "DUPLICATE_OR_LOCALIZATION"
                        if overlap_value >= 0.5 and prediction.label == truths[ti].label
                        else "CLASS_CONFUSION"
                        if overlap_value >= 0.5
                        else "NO_P0_MATCH_AT_IOU_0_5"
                    ),
                }
            )
        if result.false_positives or result.false_negatives or low_iou:
            review.append(
                {
                    "image_id": entry["image_id"],
                    "scenario": entry.get("scenario", "UNKNOWN"),
                    "low_iou_matches": low_iou,
                    "false_positive_context": fp_context,
                    "false_positives": [asdict(scoped[i]) for i in result.false_positives],
                    "false_negatives": [asdict(truths[i]) for i in result.false_negatives],
                }
            )
    return {
        "confidence": confidence,
        "iou_threshold": overlap,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "p0_micro_recall": tp / (tp + fn) if tp + fn else None,
        "miss_rate": fn / (tp + fn) if tp + fn else None,
        "attributes": {
            field: {
                label: {**count, "recall": count["matched"] / count["total"]}
                for label, count in groups.items()
            }
            for field, groups in attributes.items()
        },
        "slices": {
            field: {
                label: {
                    **counts,
                    "recall": counts["tp"] / (counts["tp"] + counts["fn"])
                    if counts["tp"] + counts["fn"]
                    else None,
                }
                for label, counts in groups.items()
            }
            for field, groups in slices.items()
        },
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
        "fp_per_100_frames": 100 * fp / len(dataset),
        "classes": {
            key: {
                **counts,
                "recall": counts["tp"] / (counts["tp"] + counts["fn"])
                if counts["tp"] + counts["fn"]
                else None,
            }
            for key, counts in by_class.items()
        },
        "sizes": {
            key: {
                **counts,
                "recall": counts["matched"] / counts["total"] if counts["total"] else None,
            }
            for key, counts in sizes.items()
        },
        "matched_mean_iou": sum(overlaps) / len(overlaps) if overlaps else None,
        "matched_mean_center_error": sum(center_errors) / len(center_errors)
        if center_errors
        else None,
        "matched_mean_bottom_error": sum(bottom_errors) / len(bottom_errors)
        if bottom_errors
        else None,
        "bottom_center_by_group": {
            group: {
                "matched_count": len(values),
                "mean_normalized_error": sum(values) / len(values) if values else None,
            }
            for group, values in localization.items()
        },
        "error_review": review,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    source_hashes = {
        path.name: file_hash(path) for path in sorted(Path(__file__).parent.glob("*.py"))
    }
    # Annotated datasets are larger than runtime configurations; retain a bound
    # and duplicate-key rejection without applying the 1 MB config-only limit.
    manifest = read_json(args.dataset, max_bytes=64_000_000)
    if manifest.get("scope") == "SENTINEL_REAL_WORLD":
        from .evaluation_dataset import EvaluationDataset, audit_dataset

        if args.annotations is None:
            raise ValueError("Real-world evaluation requires original annotation provenance")
        audit_dataset(args.dataset, args.annotations)
        manifest = EvaluationDataset.model_validate_json(args.dataset.read_bytes()).model_dump(
            mode="json"
        )
        # Select splits before inference. No calibration/test sequence may overlap.
        manifest["images"] = [e for e in manifest["images"] if e["split"] == args.split]
        for entry in manifest["images"]:
            entry.update(
                {
                    "scenario": entry["metadata"]["environment"],
                    "lighting": entry["metadata"]["lighting"],
                    "motion": entry["metadata"]["motion"],
                    "blur": entry["metadata"]["blur"],
                }
            )
    entries = manifest["images"]
    if not entries or len(entries) > 1000:
        raise ValueError("Expected 1..1000 diagnostic images")
    factories: dict[
        str,
        type[UltralyticsDetector]
        | type[RtDetrDetector]
        | type[YoloXDetector]
        | type[PicoDetDetector],
    ] = {
        "rtdetr": RtDetrDetector,
        "ultralytics": UltralyticsDetector,
        "yolox": YoloXDetector,
        "picodet": PicoDetDetector,
    }
    factory = factories[args.runtime]
    loading_started = processing_ns()
    detector = factory(
        args.weights,
        args.sha256,
        size=args.size,
        device=args.device,
        half=args.half,
        threads=args.threads,
        confidence=args.confidence_floor,
    )
    model_load_ns = processing_ns() - loading_started
    first, identity = prepare(entries[0], args.dataset.parent, 0)
    first = replace(first, pixels=stress_image(first.pixels, args.condition))
    cold_start = processing_ns()
    detector.detect(first, identity)
    cold_ns = processing_ns() - cold_start
    warmup_started = processing_ns()
    for _ in range(args.warmup):
        detector.detect(first, identity)
    warmup_ns = processing_ns() - warmup_started
    outputs: list[tuple[Detection, ...]] = []
    timings: dict[str, Distribution] = {}
    for sequence, entry in enumerate(entries):
        # File IO/decode/JVM mapping setup excluded; model color/resize/tensor work included.
        prepared, identity = prepare(entry, args.dataset.parent, sequence)
        prepared = replace(prepared, pixels=stress_image(prepared.pixels, args.condition))
        started = processing_ns()
        output = detector.detect(prepared, identity)
        elapsed = processing_ns() - started
        if output.identity != identity:
            raise ValueError("Detector changed image identity")
        outputs.append(output.detections)
        for name, ns in {**detector.last_timings_ns, "end_to_end": elapsed}.items():
            timings.setdefault(name, Distribution(len(entries))).add(ns)
    return {
        "schema_version": 1,
        "status": "MEASURED_LOCALLY",
        "dataset_sha256": file_hash(args.dataset),
        "dataset": manifest["dataset"],
        "image_count": len(entries),
        "image_ids": [item["image_id"] for item in entries],
        "candidate": asdict(detector.provenance),
        "runtime_metadata": getattr(detector, "runtime_metadata", {}),
        "model_bytes": args.weights.stat().st_size,
        "configuration": {
            "condition": args.condition,
            "size": args.size,
            "batch": 1,
            "confidence_floor": args.confidence_floor,
            "nms_iou": {"rtdetr": None, "ultralytics": 0.7, "yolox": 0.45, "picodet": 0.6}[
                args.runtime
            ],
            "max_detections": None if args.runtime == "picodet" else 300,
            "threads": args.threads,
            "warmup": args.warmup,
            "device": args.device,
            "half": args.half,
        },
        "platform": platform.platform(),
        "runtime_environment": runtime_environment(),
        "dataset_group": "SENTINEL_REAL_WORLD"
        if manifest.get("scope") == "SENTINEL_REAL_WORLD"
        else "PUBLIC_DIAGNOSTIC",
        "evaluation_split": args.split if manifest.get("scope") == "SENTINEL_REAL_WORLD" else None,
        "python": platform.python_version(),
        "dependencies": {name: version(name) for name in ("torch", "numpy", "av")},
        "source_sha256": source_hashes,
        "memory": memory_snapshot(),
        "cold_call_ns": cold_ns,
        "model_load_ns": model_load_ns,
        "warmup_ns": warmup_ns,
        "steady_latency_ns": {k: v.summary() for k, v in timings.items()},
        "latency_scope": (
            "Loaded image through DetectionBatch; excludes disk decode and geometry setup"
        ),
        "accuracy": [
            accuracy(entries, outputs, threshold, overlap)
            for overlap in (0.5, 0.75)
            for threshold in (0.05, 0.1, 0.2, 0.25, 0.4, 0.6, 0.8, 0.9)
        ],
        "predictions": [
            {"image_id": entry["image_id"], "detections": [asdict(p) for p in output]}
            for entry, output in zip(entries, outputs, strict=True)
        ],
        "missing": [
            "scenario labels",
            "occlusion labels",
            "walking video",
            "model-only peak memory",
            "mobile latency",
            "production license approval",
            "official COCO AP",
        ],
        "qualified_for_production": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--annotations", type=Path)
    parser.add_argument("--split", choices=("CALIBRATION", "TEST"), default="TEST")
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, choices=(416, 512, 640, 768), default=640)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--confidence-floor", type=float, default=0.05)
    parser.add_argument("--device", choices=("cpu", "cuda:0"), default="cpu")
    parser.add_argument("--half", action="store_true")
    parser.add_argument(
        "--runtime", choices=("ultralytics", "rtdetr", "yolox", "picodet"), default="ultralytics"
    )
    parser.add_argument(
        "--condition",
        default="original",
        choices=("original", "synthetic-dark-25pct", "synthetic-horizontal-blur-9px"),
    )
    args = parser.parse_args(argv)
    if not 0 <= args.warmup <= 100:
        parser.error("warmup must be 0..100")
    if not 0 <= args.confidence_floor <= 0.05:
        parser.error("confidence-floor must be 0..0.05 to support all reported thresholds")
    if args.output.exists():
        parser.error("Output exists; choose a new run path")
    try:
        report = run(args)
        code = 0
    except Exception as error:
        # Do not include vendor exception strings, filenames, images or environment secrets.
        report = {
            "schema_version": 1,
            "status": "FAILED",
            "error_type": type(error).__name__,
            "qualified_for_production": False,
        }
        code = 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps({"status": report["status"], "report_sha256": canonical_hash(report)}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
