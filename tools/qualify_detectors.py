"""Offline empirical threshold analysis of successful, hash-bound benchmark runs."""

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

from perception_lab.detection import P0_CLASSES, Box, Detection, ObjectClass
from perception_lab.detection_metrics import GroundTruth, evaluate
from perception_lab.detector_runtime import file_hash
from perception_lab.operating_points import OperatingPoint, select, thresholds


def analyze(report, manifest):
    if report.get("schema_version", 1) != 1:
        raise ValueError("Unsupported benchmark schema version")
    entries = manifest["images"]
    if manifest.get("scope") == "SENTINEL_REAL_WORLD":
        if not all(entry.get("annotations_reviewed") is True for entry in entries):
            raise ValueError("Real-world analysis requires human-reviewed annotations")
        if report.get("evaluation_split") not in {"CALIBRATION", "TEST"}:
            raise ValueError("Real-world run must identify evaluation split")
        entries = [e for e in entries if e["split"] == report["evaluation_split"]]
    ids = [e["image_id"] for e in entries]
    if (
        report["status"] != "MEASURED_LOCALLY"
        or report["image_ids"] != ids
        or [f["image_id"] for f in report["predictions"]] != ids
    ):
        raise ValueError("Failed, missing or misordered inference cannot become an accuracy result")
    floor = report["configuration"]["confidence_floor"]
    if report["configuration"].get("condition", "original") != "original":
        raise ValueError("Synthetic stress must have its own labeled qualification report")
    groups = {
        "P0": set(P0_CLASSES),
        "PERSON": {ObjectClass.PERSON},
        "BICYCLE": {ObjectClass.BICYCLE},
        "MOTORCYCLE": {ObjectClass.MOTORCYCLE},
        "VEHICLE": {ObjectClass.CAR, ObjectClass.BUS, ObjectClass.TRUCK, ObjectClass.TRAIN},
    }
    curves = {}
    for group, labels in groups.items():
        matched_scores, false_scores, total = [], [], 0
        for entry, frame in zip(entries, report["predictions"], strict=True):
            predictions = tuple(
                Detection(
                    d["class_id"],
                    d["class_name"],
                    ObjectClass(d["label"]),
                    d["confidence"],
                    Box(**d["box"]),
                )
                for d in frame["detections"]
                if ObjectClass(d["label"]) in labels
            )
            truth = tuple(
                GroundTruth(
                    ObjectClass(a["label"]), Box(*a["box"]), ignore=a["ignore"], crowd=a["crowd"]
                )
                for a in entry["annotations"]
                if a["label"] in labels
            )
            result = evaluate(predictions, truth, floor, 0.5)
            total += result.counts.tp + result.counts.fn
            # Confidence-greedy matching is prefix invariant: higher thresholds only
            # remove a suffix, including ignored detections. Avoid 95 redundant matches.
            matched_scores.extend(predictions[m.prediction].confidence for m in result.matches)
            false_scores.extend(predictions[i].confidence for i in result.false_positives)
        curves[group] = tuple(
            OperatingPoint(
                t,
                sum(s >= t for s in matched_scores),
                sum(s >= t for s in false_scores),
                total - sum(s >= t for s in matched_scores),
                len(entries),
            )
            for t in thresholds(floor)
        )

    def serialize(p):
        return {**asdict(p), "recall": p.recall, "precision": p.precision, "fp_per_100": p.fp100}

    points = {}
    for kind, targets in (
        ("fp100", (25, 50, 100)),
        ("precision", (0.8, 0.9, 0.95)),
        ("recall", (0.8, 0.85, 0.9, 0.95)),
    ):
        points[kind] = []
        for target in targets:
            point = select(curves["P0"], kind, target)
            points[kind].append(
                {
                    "target": target,
                    "status": "AVAILABLE" if point else "UNAVAILABLE",
                    "point": serialize(point) if point else None,
                    "groups": {
                        group: serialize(next(p for p in curve if p.threshold == point.threshold))
                        for group, curve in curves.items()
                    }
                    if point
                    else None,
                }
            )
    return {
        "candidate": report["candidate"],
        "configuration": report["configuration"],
        "dataset_sha256": report["dataset_sha256"],
        "evaluation_split": report.get("evaluation_split"),
        "image_ids": ids,
        "unavailable_thresholds": [i / 100 for i in range(1, 96) if i / 100 < floor],
        "curves": {group: [serialize(p) for p in curve] for group, curve in curves.items()},
        "operating_points": points,
    }


def freeze(calibration, manifest):
    """This function cannot inspect qualification predictions."""
    from perception_lab.evaluation_dataset import EvaluationDataset

    manifest = EvaluationDataset.model_validate_json(json.dumps(manifest)).model_dump(mode="json")
    if calibration.get("evaluation_split") != "CALIBRATION":
        raise ValueError("Threshold selection requires CALIBRATION")
    if not {"CALIBRATION", "TEST"}.issubset({e["split"] for e in manifest["images"]}):
        raise ValueError("Independent calibration and qualification sequences required")
    if any(not e["annotations_reviewed"] for e in manifest["images"]):
        raise ValueError("Reviewed annotations required")
    result = analyze(calibration, manifest)
    return {
        "schema_version": 1,
        "threshold_source": "CALIBRATION_ONLY_FROZEN",
        "candidate": calibration["candidate"],
        "configuration": calibration["configuration"],
        "dataset_sha256": calibration["dataset_sha256"],
        "operating_points": result["operating_points"],
    }


def qualify_frozen(frozen, qualification, manifest):
    from perception_lab.evaluation_dataset import EvaluationDataset

    manifest = EvaluationDataset.model_validate_json(json.dumps(manifest)).model_dump(mode="json")
    if (
        frozen.get("schema_version") != 1
        or frozen.get("threshold_source") != "CALIBRATION_ONLY_FROZEN"
    ):
        raise ValueError("Unsupported frozen threshold schema/source")
    if qualification.get("evaluation_split") != "TEST":
        raise ValueError("Qualification requires TEST sequences")
    for key in ("candidate", "configuration", "dataset_sha256"):
        if frozen[key] != qualification[key]:
            raise ValueError("Frozen model/configuration/dataset mismatch")
    result = analyze(qualification, manifest)
    points = {}
    for kind, entries in frozen["operating_points"].items():
        points[kind] = []
        for entry in entries:
            point = entry["point"]
            points[kind].append(
                {
                    "target": entry["target"],
                    "status": entry["status"],
                    "threshold_source": "CALIBRATION_ONLY_FROZEN",
                    "calibration": point,
                    "qualification": next(
                        p for p in result["curves"]["P0"] if p["threshold"] == point["threshold"]
                    )
                    if point
                    else None,
                    "qualification_groups": {
                        group: next(p for p in curve if p["threshold"] == point["threshold"])
                        for group, curve in result["curves"].items()
                    }
                    if point
                    else None,
                }
            )
    return {
        "schema_version": 1,
        "status": "HELD_OUT_QUALIFICATION",
        "operating_points": points,
        "candidate": frozen["candidate"],
        "dataset_sha256": frozen["dataset_sha256"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--runs", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--freeze", action="store_true", help="Freeze CALIBRATION thresholds before TEST inference"
    )
    parser.add_argument(
        "--frozen", type=Path, help="Evaluate TEST using an existing frozen threshold artifact"
    )
    parser.add_argument(
        "--annotations", type=Path, help="Required for split-safe real-world analysis"
    )
    args = parser.parse_args()
    if args.freeze or args.frozen:
        from perception_lab.evaluation_dataset import audit_dataset

        if args.freeze and args.frozen or len(args.runs) != 1 or args.annotations is None:
            parser.error("Use one run, --annotations, and exactly one of --freeze/--frozen")
        audit_dataset(args.dataset, args.annotations)
        manifest = json.loads(args.dataset.read_text(encoding="utf-8"))
        report = json.loads(args.runs[0].read_text(encoding="utf-8"))
        if report["dataset_sha256"] != file_hash(args.dataset):
            raise ValueError("Dataset hash mismatch")
        if args.freeze:
            document = freeze(report, manifest)
            document["calibration_run_sha256"] = file_hash(args.runs[0])
        else:
            document = qualify_frozen(
                json.loads(args.frozen.read_text(encoding="utf-8")), report, manifest
            )
            document["frozen_artifact_sha256"] = file_hash(args.frozen)
            document["qualification_run_sha256"] = file_hash(args.runs[0])
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(document, stream, indent=2)
            stream.write("\n")
        return
    outputs = [args.output.with_suffix(ext) for ext in (".json", ".csv", ".svg")]
    if any(p.exists() for p in outputs):
        parser.error("Output exists; preserve previous evidence")
    manifest = json.loads(args.dataset.read_text(encoding="utf-8"))
    if manifest.get("scope") == "SENTINEL_REAL_WORLD":
        parser.error("Real-world evaluation requires --freeze or --frozen; no post-hoc tuning")
    results = []
    for path in args.runs:
        report = json.loads(path.read_text(encoding="utf-8"))
        if report["dataset_sha256"] != file_hash(args.dataset):
            raise ValueError("Dataset hash mismatch")
        result = analyze(report, manifest)
        result["run_name"], result["run_sha256"] = path.name, file_hash(path)
        results.append(result)
    fairness = {
        (
            r["configuration"]["size"],
            r["configuration"]["threads"],
            r["configuration"]["device"],
            r["configuration"]["half"],
            r["configuration"]["confidence_floor"],
            r["evaluation_split"],
            tuple(r["image_ids"]),
        )
        for r in results
    }
    if len(fairness) != 1:
        raise ValueError("Comparison mixes resolution, threads, device, precision or score floor")
    public = manifest.get("scope") != "SENTINEL_REAL_WORLD"
    document = {
        "schema_version": 1,
        "dataset_group": "PUBLIC_DIAGNOSTIC" if public else "SENTINEL_REAL_WORLD",
        "dataset_classification": "DIAGNOSTIC_PUBLIC_SUBSET" if public else "SENTINEL_REAL_WORLD",
        "calibration": "POST_HOC_SAME_EVALUATION_SET; descriptive only, not held-out qualification",
        "iou_threshold": 0.5,
        "vehicle_definition": "CAR BUS TRUCK TRAIN; excludes two-wheelers",
        "selection": "observed grid points, no interpolation or extrapolation",
        "runs": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    outputs[0].write_text(json.dumps(document, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    with outputs[1].open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            (
                "run",
                "group",
                "threshold",
                "tp",
                "fp",
                "fn",
                "frames",
                "recall",
                "precision",
                "fp100",
            )
        )
        for result in results:
            for group, curve in result["curves"].items():
                for p in curve:
                    writer.writerow(
                        (
                            result["run_name"],
                            group,
                            p["threshold"],
                            p["tp"],
                            p["fp"],
                            p["fn"],
                            p["frames"],
                            p["recall"],
                            p["precision"],
                            p["fp_per_100"],
                        )
                    )
    # Plotting is optional research tooling, not a dependency of the runtime/CI tests.
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for ax, group in zip(axes.flat, results[0]["curves"], strict=False):
        for result in results:
            points = [
                p
                for p in result["curves"][group]
                if p["recall"] is not None and p["precision"] is not None
            ]
            ax.plot(
                [p["recall"] for p in points],
                [p["precision"] for p in points],
                label=result["run_name"].removesuffix(".json"),
                marker=".",
                markersize=2,
            )
        ax.set(xlabel="Recall", ylabel="Precision", title=group, xlim=(0, 1), ylim=(0, 1))
        ax.grid(alpha=0.3)
    axes.flat[-1].axis("off")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    axes.flat[-1].legend(handles, labels, loc="center", fontsize=8)
    fig.suptitle(document["dataset_group"] + " — empirical PR, same-set threshold analysis")
    fig.tight_layout()
    fig.savefig(outputs[2])
    plt.close(fig)
    print(json.dumps({"runs": len(results), "dataset_group": document["dataset_group"]}))


if __name__ == "__main__":
    main()
