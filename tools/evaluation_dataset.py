"""Local-only PTS frame export, COCO annotation import and evaluation validation."""

import argparse
import json
from pathlib import Path

import av

from perception_lab.detection import COCO_CATEGORIES
from perception_lab.detector_runtime import file_hash
from perception_lab.evaluation_dataset import (
    EvaluationDataset,
    audit_dataset,
    sample_indices,
)
from perception_lab.first_person import allocate, discover, event_sample_indices


def export(args):
    if args.output.exists():
        raise ValueError("Export directory must be new")
    source_hash = file_hash(args.video)
    pts = []
    with av.open(
        str(args.video),
        options={"format_whitelist": "mov,matroska,webm,avi", "protocol_whitelist": "file"},
    ) as container:
        for frame in container.decode(video=0):
            if frame.pts is None or frame.time_base is None:
                raise ValueError("Source has missing presentation timestamps")
            pts.append(int(frame.pts * frame.time_base * 1_000_000_000))
            if len(pts) > 100_000:
                raise ValueError("Use a short source clip (maximum 100000 decoded frames)")
    windows = getattr(args, "event_windows", None)
    selected = set(
        event_sample_indices(pts, tuple(tuple(w) for w in windows))
        if windows is not None
        else sample_indices(pts, args.fps)
    )
    if len(selected) > 1000:
        raise ValueError("Use a shorter clip; maximum 1000 exported frames")
    args.output.mkdir(parents=True)
    entries = []
    with av.open(
        str(args.video),
        options={"format_whitelist": "mov,matroska,webm,avi", "protocol_whitelist": "file"},
    ) as container:
        for index, frame in enumerate(container.decode(video=0)):
            if index not in selected:
                continue
            path = args.output / f"frame-{index:06d}.ppm"
            pixels = frame.to_ndarray(format="rgb24")
            path.write_bytes(f"P6\n{frame.width} {frame.height}\n255\n".encode() + pixels.tobytes())
            entries.append(
                {
                    "image_id": f"{args.sequence}-{index}",
                    "sequence_id": args.sequence,
                    "split": args.split,
                    "observation_ns": pts[index],
                    "path": path.name,
                    "sha256": file_hash(path),
                    "width": frame.width,
                    "height": frame.height,
                    "coordinate_space": "ORIGINAL_CAMERA_CONTINUOUS_EDGES",
                    "annotations_reviewed": False,
                    "metadata": dict.fromkeys(
                        ("lighting", "motion", "occlusion", "environment", "blur", "provenance"),
                        "UNKNOWN",
                    ),
                    "annotations": [],
                }
            )
    if file_hash(args.video) != source_hash:
        raise ValueError("Source media changed during sampling; discard this incomplete export")
    manifest = {
        "schema_version": 1,
        "dataset": args.sequence,
        "scope": "SENTINEL_REAL_WORLD",
        "annotation_sha256": "0" * 64,
        "sequences": [
            {
                "sequence_id": args.sequence,
                "media_sha256": source_hash,
                "source_url_or_reference": args.source,
                "license_reference": args.license,
                "permission_status": "REVIEW_REQUIRED",
                "sampling_fps": args.fps,
                "sampling_policy": json.dumps(
                    {
                        "rule": "First PTS on/after anchored grid; no duplicate frames",
                        "base_fps": args.fps,
                        "event_fps": 5 if windows is not None else None,
                        "event_windows_ns": windows,
                        "split_seed": getattr(args, "seed", None),
                    },
                    sort_keys=True,
                ),
            }
        ],
        "images": entries,
    }
    (args.output / "manifest.draft.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"exported": len(entries), "status": "DRAFT_NOT_GROUND_TRUTH"}))


def import_coco(args):
    if args.output.exists():
        raise ValueError("Output exists")
    if args.output.parent.resolve() != args.manifest.parent.resolve():
        raise ValueError("Imported manifest must stay beside its relative image paths")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    coco = json.loads(args.annotations.read_text(encoding="utf-8"))
    # Use category names: custom COCO exports frequently renumber category IDs.
    known = {value.value.lower(): value.value for value in COCO_CATEGORIES.values()}
    categories = {c["id"]: known.get(c["name"].lower()) for c in coco["categories"]}
    if len(categories) != len(coco["categories"]):
        raise ValueError("Duplicate COCO category ID")
    images = {i["id"]: i for i in coco["images"]}
    entries = {entry["path"]: entry for entry in manifest["images"]}
    if len(images) != len(coco["images"]) or len(entries) != len(manifest["images"]):
        raise ValueError("Duplicate image ID/path")
    if {i["file_name"] for i in images.values()} != set(entries):
        raise ValueError("COCO frame list must exactly match exported frames")
    if len(images) != len(entries):
        raise ValueError("Duplicate COCO image filename")
    for source in images.values():
        entry = entries[source["file_name"]]
        if (entry["width"], entry["height"]) != (source["width"], source["height"]):
            raise ValueError("COCO coordinates refer to different image dimensions")
        entry["annotations"] = []
        entry["annotations_reviewed"] = False
    for annotation in coco["annotations"]:
        label = categories[annotation["category_id"]]
        if label is None:
            continue  # Explicitly evaluate P0 only; non-P0 objects are not P0 negatives.
        source = images[annotation["image_id"]]
        x, y, width, height = annotation["bbox"]
        entries[source["file_name"]]["annotations"].append(
            {
                "label": label,
                "box": [x, y, x + width, y + height],
                "ignore": coco_flag(annotation.get("ignore", False)),
                "crowd": coco_flag(annotation.get("iscrowd", False)),
                "truncated": annotation.get("truncated"),
                "occluded": annotation.get("occluded"),
            }
        )
    manifest["annotation_sha256"] = file_hash(args.annotations)
    EvaluationDataset.model_validate_json(json.dumps(manifest))
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Imported. Human annotation/scenario and permission review still required.")


def coco_flag(value):
    if type(value) not in {bool, int} or value not in (0, 1):
        raise ValueError("COCO ignore/crowd flags must be boolean or integer 0/1")
    return bool(value)


def ingest(args):
    from types import SimpleNamespace

    videos = discover(args.raw)
    allocation = allocate(videos, args.seed)
    if not videos:
        print(json.dumps({"status": "DATA_PENDING", "real_videos": 0}))
        return
    if args.output.exists():
        raise ValueError("Output exists; preserve the frozen split")
    windows = json.loads(args.events.read_text(encoding="utf-8")) if args.events else {}
    if set(windows) - {sequence for sequence, _ in allocation.values()}:
        raise ValueError("Unknown sequence in event-window configuration")
    args.output.mkdir(parents=True)
    merged = None
    for video, (sequence, split) in allocation.items():
        directory = args.output / sequence
        export(
            SimpleNamespace(
                video=video,
                output=directory,
                sequence=sequence,
                split=split,
                fps=2.0,
                source="USER_OWNED_LOCAL_VIDEO",
                license="USER_OWNERSHIP_REVIEW_REQUIRED",
                event_windows=windows.get(sequence, []),
                seed=args.seed,
            )
        )
        draft = json.loads((directory / "manifest.draft.json").read_text(encoding="utf-8"))
        for entry in draft["images"]:
            entry["path"] = sequence + "/" + entry["path"]
        if merged is None:
            merged = draft
        else:
            merged["images"].extend(draft["images"])
            merged["sequences"].extend(draft["sequences"])
    merged["dataset"] = "SENTINEL_FIRST_PERSON_V1"
    EvaluationDataset.model_validate_json(json.dumps(merged))
    (args.output / "manifest.draft.json").write_text(
        json.dumps(merged, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "ANNOTATION_PENDING",
                "real_videos": len(videos),
                "frames": len(merged["images"]),
                "seed": args.seed,
                "split_status": "AVAILABLE" if len(videos) >= 2 else "NEED_SECOND_SEQUENCE",
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    ingest_parser = sub.add_parser("ingest")
    ingest_parser.add_argument(
        "--raw", type=Path, default=Path("datasets/sentinel_first_person_v1/raw")
    )
    ingest_parser.add_argument(
        "--output", type=Path, default=Path("datasets/sentinel_first_person_v1/work")
    )
    ingest_parser.add_argument("--events", type=Path)
    ingest_parser.add_argument("--seed", type=int, default=0)
    export_parser = sub.add_parser("export")
    export_parser.add_argument("--video", type=Path, required=True)
    export_parser.add_argument("--output", type=Path, required=True)
    export_parser.add_argument("--sequence", required=True)
    export_parser.add_argument("--source", required=True)
    export_parser.add_argument("--license", required=True)
    export_parser.add_argument("--split", choices=("CALIBRATION", "TEST"), required=True)
    export_parser.add_argument("--fps", type=float, default=2.0)
    for action in ("import-coco", "validate"):
        item = sub.add_parser(action)
        item.add_argument("--manifest", type=Path, required=True)
        item.add_argument("--annotations", type=Path, required=True)
        if action == "import-coco":
            item.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "ingest":
        ingest(args)
    elif args.action == "export":
        export(args)
    elif args.action == "import-coco":
        import_coco(args)
    else:
        print(json.dumps(audit_dataset(args.manifest, args.annotations), indent=2))


if __name__ == "__main__":
    main()
