"""Prepare local model-assisted drafts and a small offline box editor; never auto-review."""

import argparse
import json
import re
from dataclasses import asdict
from pathlib import Path

from perception_lab.detection import P0_CLASSES, Box
from perception_lab.detection_metrics import iou
from perception_lab.detector_benchmark import prepare
from perception_lab.detector_runtime import file_hash
from perception_lab.edge_runtime import PINS, PicoDetDetector, YoloXDetector
from perception_lab.evaluation_dataset import EvaluationDataset


def propose(root, model_root):
    manifest_path = root / "manifest.draft.json"
    manifest = EvaluationDataset.model_validate_json(manifest_path.read_bytes()).model_dump(
        mode="json"
    )
    output = root / "annotations" / "model-assisted.json"
    if output.exists():
        raise ValueError("Proposals exist; never overwrite review work")
    models = [
        YoloXDetector(model_root / "yolox_nano.onnx", PINS["yolox-nano"], confidence=0.2),
        PicoDetDetector(model_root / "picodet_s_416.onnx", PINS["picodet-s"], confidence=0.25),
    ]
    for index, entry in enumerate(manifest["images"]):
        image, identity = prepare(entry, root, index)
        proposals = []
        for model in models:
            batch = model.detect(image, identity)
            if batch.identity != identity:
                raise ValueError("Model changed identity")
            for detection in batch.detections:
                if detection.label not in P0_CLASSES:
                    continue
                b = detection.box
                clipped = Box(
                    max(0, min(entry["width"], b.x1)),
                    max(0, min(entry["height"], b.y1)),
                    max(0, min(entry["width"], b.x2)),
                    max(0, min(entry["height"], b.y2)),
                )
                if clipped.area <= 0 or any(
                    a["label"] == detection.label.value and iou(clipped, Box(*a["box"])) > 0.85
                    for a in proposals
                ):
                    continue
                proposals.append(
                    {
                        "label": detection.label.value,
                        "box": list(clipped.coordinates),
                        "ignore": False,
                        "crowd": False,
                    }
                )
        entry["annotations"] = proposals
        entry["annotations_reviewed"] = False
        if index % 25 == 0:
            print(json.dumps({"proposed_frames": index + 1}), flush=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output.parent / "proposal-provenance.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "DRAFT_MODEL_ASSISTED",
                "input_manifest_sha256": file_hash(manifest_path),
                "models": [asdict(model.provenance) for model in models],
                "merge": "Same-class IoU > .85 suppression; first model retained; draft only",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    template = (Path(__file__).parent / "annotation-review.html").read_text(encoding="utf-8")
    rendered, count = re.subn(
        r"/\*SENTINEL_DATA\*/\s*null",
        lambda _: json.dumps(manifest).replace("<", "\\u003c"),
        template,
    )
    if count != 1:
        raise ValueError("Review template must contain exactly one data placeholder")
    (root / "review.html").write_text(rendered, encoding="utf-8")
    print(
        json.dumps(
            {
                "review_frames": len(manifest["images"]),
                "status": "HUMAN_GROUND_TRUTH_REVIEW_REQUIRED",
            }
        )
    )


def finalize(root, review):
    data = EvaluationDataset.model_validate_json(review.read_bytes()).model_dump(mode="json")
    original = EvaluationDataset.model_validate_json(
        (root / "manifest.draft.json").read_bytes()
    ).model_dump(mode="json")
    if (
        data["sequences"] != original["sequences"]
        or data["dataset"] != original["dataset"]
        or len(data["images"]) != len(original["images"])
    ):
        raise ValueError("Review changed frozen dataset identity")
    editable = {"annotations", "annotations_reviewed", "metadata"}
    for frame, source in zip(data["images"], original["images"], strict=True):
        if {k: v for k, v in frame.items() if k not in editable} != {
            k: v for k, v in source.items() if k not in editable
        }:
            raise ValueError("Review changed frozen frame identity")
        if not frame["annotations_reviewed"]:
            raise ValueError("Human frame review incomplete")
    data["annotation_sha256"] = file_hash(review)
    with (root / "manifest.reviewed.json").open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")
    print("Review imported. Run evaluation_dataset.py validate before benchmarking.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("datasets/sentinel_first_person_v1"))
    parser.add_argument("--models", type=Path, default=Path("benchmark-results/task006c/models"))
    parser.add_argument("--review", type=Path)
    args = parser.parse_args()
    if args.review:
        finalize(args.root, args.review)
    else:
        propose(args.root, args.models)
