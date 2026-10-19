"""Bounded tracking experiments. Reviewed IDs required for real identity metrics."""

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from time import perf_counter_ns

import av
import numpy as np

from perception_lab.config import Calibration, PreprocessConfig, read_json
from perception_lab.contracts import (
    ComponentProvenance,
    Frame,
    FrameIdentity,
    PixelFormat,
    TimingProvenance,
)
from perception_lab.detection import Box, Detection, DetectionBatch, ObjectClass
from perception_lab.detector_runtime import file_hash
from perception_lab.edge_runtime import PicoDetDetector, YoloXDetector
from perception_lab.geometry import CoreGeometry
from perception_lab.metrics import Distribution
from perception_lab.preprocessing import BasicPreprocessor
from perception_lab.tracking import AssociationTracker
from perception_lab.tracking_config import TrackerConfig
from perception_lab.tracking_dataset import TrackingDataset, validate_review
from perception_lab.tracking_evaluation import LabeledBox, evaluate_sequence
from perception_lab.tracking_types import DetectorEvidence, Lifecycle

BASELINES = [
    ("iou", "alpha_beta"),
    ("motion", "alpha_beta"),
    ("motion", "kalman"),
    ("two_stage", "alpha_beta"),
    ("two_stage", "kalman"),
]


def cache(args):
    packet = TrackingDataset.model_validate_json(args.draft.read_bytes())
    factory = {"picodet": PicoDetDetector, "yolox": YoloXDetector}[args.runtime]
    detector = factory(args.weights, args.sha256, size=416, confidence=0.1, threads=1)
    calibration = Calibration.model_validate(read_json(args.calibration))
    pre = BasicPreprocessor(CoreGeometry(calibration), PreprocessConfig())
    output = []
    for sequence, f in enumerate(packet.frames):
        path = (args.draft.parent / f.path).resolve()
        if not path.is_relative_to(args.draft.parent.resolve()) or file_hash(path) != f.sha256:
            raise ValueError("Image provenance mismatch")
        with av.open(
            str(path),
            options={
                "protocol_whitelist": "file",
                "format_whitelist": "jpeg_pipe,image2",
            },
        ) as container:
            pixels = next(container.decode(video=0)).to_ndarray(format="rgb24")
        identity = FrameIdentity(
            f.clip_id, sequence, f.observation_ns, TimingProvenance.AUTHORITATIVE_PTS
        )
        frame = Frame(identity, np.ascontiguousarray(pixels), PixelFormat.RGB, 0, 0)
        batch = detector.detect(pre.prepare(frame), identity)
        output.append({"image_id": f.image_id, "batch": asdict(batch)})
    return {
        "schema_version": 1,
        "dataset_sha256": file_hash(args.draft),
        "score_floor": 0.1,
        "status": "PREDICTIONS_NOT_GROUND_TRUTH",
        "frames": output,
    }


def parse_batch(data):
    ident = data["identity"]
    identity = FrameIdentity(
        ident["source_id"],
        ident["sequence"],
        ident["observation_ns"],
        TimingProvenance(ident["timing"]),
    )
    detections = tuple(
        Detection(
            d["class_id"],
            d["class_name"],
            ObjectClass(d["label"]),
            d["confidence"],
            Box(**d["box"]),
        )
        for d in data["detections"]
    )
    return DetectionBatch(
        identity,
        detections,
        ComponentProvenance(**data["provenance"]),
        data["transform_hash"],
        data["inference_ns"],
        data["postprocess_ns"],
        data["taxonomy_version"],
    )


def run_sequence(batches, truth, config, session, width=1906, height=876, cadence=1):
    tracker = AssociationTracker(config, session, batches[0].identity.source_id, width, height)
    latency = Distribution(10000)
    evaluated = []
    peak = history_peak = 0
    confirmations = {}
    prediction_ages = Distribution(10000)
    diagnostic_counts = {}
    for i, batch in enumerate(batches):
        scheduled = i % cadence == 0
        evidence = (
            (DetectorEvidence.SUCCESS if batch.detections else DetectorEvidence.SUCCESS_EMPTY)
            if scheduled
            else DetectorEvidence.NO_DETECTOR_RUN
        )
        started = perf_counter_ns()
        result = tracker.update(session, batch.identity, evidence, batch if scheduled else None)
        latency.add(perf_counter_ns() - started)
        peak = max(peak, len(result.tracks))
        history_peak = max(history_peak, sum(len(t.history) for t in result.tracks))
        for code in result.diagnostics:
            diagnostic_counts[code] = diagnostic_counts.get(code, 0) + 1
        for t in result.tracks:
            if t.lifecycle == Lifecycle.CONFIRMED:
                confirmations.setdefault(t.track_id.serial, t.age_ns)
            if t.observation_status == "PREDICTED":
                prediction_ages.add(t.observation_age_ns)
        prediction = tuple(
            LabeledBox(str(t.track_id.serial), t.category, t.bbox)
            for t in result.tracks
            if t.lifecycle in (Lifecycle.CONFIRMED, Lifecycle.LOST)
        )
        if truth is not None:
            evaluated.append((truth[i], prediction))
    tracker.close()
    return {
        "configuration": config.model_dump(),
        "cadence_divisor": cadence,
        "frames": len(batches),
        "detector_runs": sum(i % cadence == 0 for i in range(len(batches))),
        "peak_active_tracks": peak,
        "peak_history_entries": history_peak,
        "latency_ns": latency.summary(),
        "confirmation_time_ns": sorted(confirmations.values()),
        "prediction_age_ns": prediction_ages.summary(),
        "diagnostics": diagnostic_counts,
        "metrics": evaluate_sequence(evaluated) if truth is not None else None,
        "per_class_metrics": {
            label.value: evaluate_sequence(
                [
                    (
                        tuple(g for g in ground if g.category == label),
                        tuple(p for p in predicted if p.category == label),
                    )
                    for ground, predicted in evaluated
                ]
            )
            for label in ObjectClass
            if label != ObjectClass.UNKNOWN
        }
        if truth is not None
        else None,
        "publication_policy": "CONFIRMED_AND_LOST_INCLUDING_PREDICTIONS",
    }


def synthetic():
    batches, truth = [], []
    provenance = ComponentProvenance("analytical-fixture", "detector")
    for i in range(160):
        identity = FrameIdentity("synthetic", i, i * 40_000_000, TimingProvenance.SYNTHETIC)
        boxes = [
            Box(10 + i * 2, 10, 30 + i * 2, 50),
            Box(340 - i * 2, 10, 360 - i * 2, 50),
            Box(200, 100, 220, 140),
        ]
        labels = [ObjectClass.PERSON, ObjectClass.PERSON, ObjectClass.BICYCLE]
        truth.append(tuple(LabeledBox(str(j), labels[j], box) for j, box in enumerate(boxes)))
        ds = []
        for j, box in enumerate(boxes):
            if (j == 0 and 45 <= i <= 49) or (j == 1 and 90 <= i <= 120):
                continue
            label = ObjectClass.MOTORCYCLE if j == 2 and i % 11 == 0 else labels[j]
            score = 0.15 if j == 0 and 30 <= i <= 36 else 0.9
            ds.append(Detection(j, label.value.lower(), label, score, box))
        if i in (10, 30, 60):
            ds.append(Detection(0, "person", ObjectClass.PERSON, 0.8, Box(450, 200, 470, 240)))
        batches.append(DetectionBatch(identity, tuple(ds), provenance, "a" * 64, 0, 0))
    runs = []
    for kind, motion in BASELINES:
        for cadence in (1, 2, 5):
            runs.append(
                run_sequence(
                    batches,
                    truth,
                    TrackerConfig(tracker_type=kind, motion_model=motion),
                    "synthetic",
                    640,
                    480,
                    cadence,
                )
            )
    # Confirmation/removal policy sensitivity is synthetic development evidence only.
    for hits in (2, 4):
        for gap in (400_000_000, 1_500_000_000):
            runs.append(
                run_sequence(
                    batches,
                    truth,
                    TrackerConfig(minimum_hits=hits, max_unobserved_ns=gap),
                    "synthetic",
                    640,
                    480,
                )
            )
    return {
        "schema_version": 1,
        "scope": "SYNTHETIC_ANALYTICAL_NOT_REAL_WORLD",
        "runs": runs,
    }


def real(args):
    packet = TrackingDataset.model_validate_json(args.draft.read_bytes())
    reviewed = validate_review(args.draft, args.review) if args.review else None
    cache_data = json.loads(args.predictions.read_text())
    if cache_data["dataset_sha256"] != file_hash(args.draft):
        raise ValueError("Prediction packet mismatch")
    cache_frames = cache_data["frames"]
    if [r["image_id"] for r in cache_frames] != [f.image_id for f in packet.frames]:
        raise ValueError("Prediction frame mismatch")
    runs = []
    for clip in sorted({f.clip_id for f in packet.frames}):
        indices = [i for i, f in enumerate(packet.frames) if f.clip_id == clip]
        batches = [parse_batch(cache_frames[i]["batch"]) for i in indices]
        if any(
            b.identity.source_id != clip
            or b.identity.observation_ns != packet.frames[i].observation_ns
            for b, i in zip(batches, indices, strict=True)
        ):
            raise ValueError("Prediction timestamp mismatch")
        truth = (
            [
                tuple(
                    LabeledBox(a.ground_truth_track_id, ObjectClass(a.label), Box(*a.box))
                    for a in reviewed.frames[i].annotations
                )
                for i in indices
            ]
            if reviewed
            else None
        )
        for kind, motion in BASELINES:
            for cadence in (1, 2):
                config = TrackerConfig(
                    tracker_type=kind,
                    motion_model=motion,
                    publication_threshold=args.publication_threshold,
                )
                result = run_sequence(
                    batches,
                    truth,
                    config,
                    clip,
                    packet.frames[indices[0]].width,
                    packet.frames[indices[0]].height,
                    cadence,
                )
                result["clip"] = clip
                result["actual_detector_hz"] = packet.sampling_fps / cadence
                runs.append(result)
    return {
        "schema_version": 1,
        "scope": "REVIEWED_DEVELOPMENT_TRACKING" if reviewed else "UNREVIEWED_RUNTIME_ONLY",
        "review_sha256": file_hash(args.review) if reviewed else None,
        "prediction_sha256": file_hash(args.predictions),
        "draft_sha256": file_hash(args.draft),
        "identity_metrics_status": "MEASURED"
        if reviewed
        else "HUMAN_TRACK_GROUND_TRUTH_REVIEW_REQUIRED",
        "runs": runs,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("synthetic", "cache", "real"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--draft", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--runtime", choices=("picodet", "yolox"))
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--calibration", type=Path)
    parser.add_argument("--publication-threshold", type=float, default=0.25)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve previous results")
    document = (
        synthetic()
        if args.mode == "synthetic"
        else cache(args)
        if args.mode == "cache"
        else real(args)
    )
    root = Path(__file__).resolve().parents[1]
    document["software_sha256"] = {
        str(path.relative_to(root)).replace("\\", "/"): file_hash(path)
        for path in sorted((root / "apps/perception-lab/src/perception_lab").glob("tracking*.py"))
    }
    document["software_sha256"]["tools/tracking_benchmark.py"] = file_hash(Path(__file__))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(document, stream, indent=2, allow_nan=False)
    if "runs" in document:
        with args.output.with_suffix(".csv").open("x", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(
                [
                    "clip",
                    "tracker",
                    "motion",
                    "cadence_divisor",
                    "frames",
                    "peak_tracks",
                    "p50_ns",
                    "p90_ns",
                    "p95_ns",
                    "p99_ns",
                    "id_switches",
                    "identity_f1",
                ]
            )
            for r in document["runs"]:
                m = r["metrics"] or {}
                writer.writerow(
                    [
                        r.get("clip", "synthetic"),
                        r["configuration"]["tracker_type"],
                        r["configuration"]["motion_model"],
                        r["cadence_divisor"],
                        r["frames"],
                        r["peak_active_tracks"],
                        *[r["latency_ns"][f"p{q}_ns"] for q in (50, 90, 95, 99)],
                        m.get("id_switches"),
                        m.get("identity_f1"),
                    ]
                )
    print(
        json.dumps(
            {
                "status": document.get("scope", document.get("status")),
                "runs": len(document.get("runs", [])),
            }
        )
    )
