"""Publish compact, reproducible research evidence from explicitly selected local runs."""

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

from perception_lab.detection import Box, Detection, ObjectClass
from perception_lab.detection_metrics import CandidateScore, pareto_front
from perception_lab.detection_parity import compare
from perception_lab.detector_benchmark import accuracy as evaluate_accuracy
from perception_lab.detector_runtime import file_hash


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def detections(frame):
    return tuple(
        Detection(
            d["class_id"],
            d["class_name"],
            ObjectClass(d["label"]),
            d["confidence"],
            Box(**d["box"]),
        )
        for d in frame["detections"]
    )


def summarize(path, dataset):
    report = read(path)
    if report["status"] != "MEASURED_LOCALLY":
        raise ValueError(f"Failed run: {path.name}")
    ids = [entry["image_id"] for entry in dataset]
    if report["image_ids"] != ids or [p["image_id"] for p in report["predictions"]] != ids:
        raise ValueError("Prediction/dataset ordering mismatch")
    if any(
        report["configuration"][k] != v
        for k, v in {
            "batch": 1,
            "threads": 1,
            "confidence_floor": 0.05,
            "device": "cpu",
            "half": False,
        }.items()
    ):
        raise ValueError("Expected controlled batch-one one-thread CPU FP32 comparison")
    report["accuracy"] = [
        evaluate_accuracy(
            dataset, [detections(p) for p in report["predictions"]], threshold, overlap
        )
        for overlap in (0.5, 0.75)
        for threshold in (0.05, 0.1, 0.2, 0.25, 0.4, 0.6, 0.8, 0.9)
    ]
    accuracy = next(
        a for a in report["accuracy"] if a["confidence"] == 0.25 and a["iou_threshold"] == 0.5
    )
    classes = accuracy["classes"]
    vehicles = [classes[k] for k in ("BICYCLE", "MOTORCYCLE", "CAR", "BUS", "TRUCK", "TRAIN")]
    vehicle_total = sum(c["tp"] + c["fn"] for c in vehicles)
    latency = report["steady_latency_ns"]
    metadata = report["runtime_metadata"]
    rtdetr = report["candidate"]["model_id"].startswith("rtdetr")
    row = {
        "run": path.stem,
        "report_sha256": file_hash(path),
        "candidate": report["candidate"]["model_id"],
        "runtime": metadata["artifact_format"],
        "precision": "FP32",
        "input_size": report["configuration"]["size"],
        "condition": report["configuration"]["condition"],
        "confidence": 0.25,
        "iou_threshold": 0.5,
        "p0_recall": accuracy["p0_micro_recall"],
        "macro_p0_recall": sum(c["recall"] for c in classes.values() if c["recall"] is not None)
        / sum(c["recall"] is not None for c in classes.values()),
        "pedestrian_recall": classes["PERSON"]["recall"],
        "vehicle_recall": sum(c["tp"] for c in vehicles) / vehicle_total if vehicle_total else None,
        "bicycle_recall": classes["BICYCLE"]["recall"],
        "motorcycle_recall": classes["MOTORCYCLE"]["recall"],
        "tiny_recall": accuracy["sizes"]["TINY"]["recall"],
        "small_recall": accuracy["sizes"]["SMALL"]["recall"],
        "occluded_recall": None,
        "fp_per_100_frames": accuracy["fp_per_100_frames"],
        "mean_iou": accuracy["matched_mean_iou"],
        "bottom_center_error": accuracy["matched_mean_bottom_error"],
        "center_error": accuracy["matched_mean_center_error"],
        "inference_p95_ms": latency["inference"]["p95_ns"] / 1e6,
        "preprocess_total_p95_ms": latency["preprocess_total"]["p95_ns"] / 1e6
        if "preprocess_total" in latency
        else None,
        "postprocess_total_p95_ms": latency["postprocess_total"]["p95_ns"] / 1e6
        if "postprocess_total" in latency
        else None,
        "vendor_preprocess_p95_ms": latency["vendor_preprocess"]["p95_ns"] / 1e6,
        "vendor_postprocess_p95_ms": latency.get(
            "vendor_postprocess", latency.get("postprocess_and_restoration")
        )["p95_ns"]
        / 1e6,
        "end_to_end_p95_ms": latency["end_to_end"]["p95_ns"] / 1e6,
        "end_to_end_p99_ms": latency["end_to_end"]["p99_ns"] / 1e6,
        "loaded_image_throughput_fps": 1e9 / latency["end_to_end"]["mean_ns"],
        "model_bytes": report["model_bytes"],
        "parameter_count": metadata.get(
            "parameter_count",
            metadata.get("parameter_count_loaded", metadata.get("parameter_count_unfused")),
        ),
        "peak_process_working_set_bytes": report.get("memory", {}).get("peak_working_set_bytes"),
        "license": "Apache-2.0; review required"
        if rtdetr
        else "AGPL-3.0 / enterprise; review required",
        "mobile_export": "UNVERIFIED",
    }
    details = {
        "platform": report["platform"],
        "python": report["python"],
        "dependencies": report["dependencies"],
        "provenance": report["candidate"],
        "runtime_metadata": metadata,
        "configuration": report["configuration"],
        "memory": report.get("memory"),
        "latency_ns": latency,
        "cold_call_ns": report["cold_call_ns"],
        "model_load_ns": report["model_load_ns"],
        "warmup_ns": report["warmup_ns"],
        "threshold_sweeps": [
            {k: v for k, v in a.items() if k != "error_review"} for a in report["accuracy"]
        ],
        "source_sha256": report.get("source_sha256"),
    }
    return row, details, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, default=Path("benchmark-results/task006"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--hardware", type=Path, help="Verified machine metadata JSON, if available"
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("datasets/raw/coco2017/sentinel-subset.json"),
    )
    args = parser.parse_args()
    paths = sorted(args.runs.glob("*-controlled.json"))
    paths += sorted(args.runs.glob("*-640-onnx.json"))
    paths += sorted(args.runs.glob("*-640-repeat.json"))
    paths += sorted(args.runs.glob("*-640-synthetic-*.json"))
    if len(paths) < 10:
        raise ValueError("Expected complete controlled native baseline")
    rows, details, reports, manifests = [], {}, {}, set()
    dataset = read(args.dataset)["images"]
    errors = {}
    for path in paths:
        row, detail, report = summarize(path, dataset)
        if report["dataset_sha256"] != file_hash(args.dataset):
            raise ValueError("Dataset integrity mismatch")
        rows.append(row)
        details[path.stem] = detail
        reports[path.stem] = report
        if path.stem.endswith("640-controlled"):
            review = next(
                a["error_review"]
                for a in report["accuracy"]
                if a["confidence"] == 0.25 and a["iou_threshold"] == 0.5
            )
            errors[path.stem] = [
                {k: v[:20] if isinstance(v, list) else v for k, v in frame.items()}
                for frame in review
            ]
        manifests.add((report["dataset_sha256"], tuple(report["image_ids"])))
    if len(manifests) != 1:
        raise ValueError("Cannot compare different datasets/image orders")
    parity = {}
    for name in ("yolo26n", "yolo26s", "yolo11n", "rtdetr-v2-r18"):
        native = reports.get(f"{name}-640-controlled")
        exported = reports.get(f"{name}-640-onnx")
        if exported is None:
            continue
        frames = []
        for left, right in zip(native["predictions"], exported["predictions"], strict=True):
            if left["image_id"] != right["image_id"]:
                raise ValueError("Parity frame mismatch")
            result = compare(detections(left), detections(right))
            frames.append(
                {
                    "image_id": left["image_id"],
                    **asdict(result),
                    "passed": result.passed,
                }
            )
        parity[name] = {
            "score_tolerance": 0.001,
            "box_edge_tolerance_pixels": 0.5,
            "confidence_floor": 0.05,
            "passed": all(f["passed"] for f in frames),
            "frames": frames,
        }
    scores = tuple(
        CandidateScore(
            r["run"],
            r["p0_recall"],
            r["end_to_end_p95_ms"],
            r["fp_per_100_frames"],
            False,
            False,
        )
        for r in rows
        if r["condition"] == "original"
    )
    result = {
        "schema_version": 1,
        "status": "MEASURED_LOCALLY",
        "dataset_sha256": next(iter(manifests))[0],
        "scope": "36 class-selected COCO stills; diagnostic only; no production qualification",
        "hardware": read(args.hardware) if args.hardware else None,
        "analysis_source_sha256": {
            "summarizer": file_hash(Path(__file__)),
            "metrics": file_hash(Path(evaluate_accuracy.__code__.co_filename)),
        },
        "matrix": rows,
        "runs": details,
        "parity": parity,
        "exports_at_creation": {
            p.relative_to(args.runs).as_posix(): read(p)
            for p in sorted((args.runs / "models").rglob("*.export.json"))
        },
        "accuracy_latency_pareto": [s.name for s in pareto_front(scores)],
        "qualified_production_candidates": [],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    args.output.with_suffix(".errors.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "confidence": 0.25,
                "iou": 0.5,
                "media_copied": False,
                "max_examples_per_kind_per_frame": 20,
                "scope": "native 640 baseline; full examples retained in local raw reports",
                "review": errors,
            },
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    with args.output.with_suffix(".csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(
        json.dumps(
            {
                "runs": len(rows),
                "parity": {k: v["passed"] for k, v in parity.items()},
                "pareto": result["accuracy_latency_pareto"],
            }
        )
    )


if __name__ == "__main__":
    main()
