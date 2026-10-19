"""Local immutable-media inventory, guarded temporal splits and review-frame preparation."""

import argparse
import json
import subprocess
from pathlib import Path

import av
import numpy as np

from perception_lab.config import canonical_hash
from perception_lab.detector_runtime import file_hash
from perception_lab.evaluation_dataset import EvaluationDataset
from perception_lab.first_person import discover


def windows(start, end):
    usable = end - start - 120_000_000_000
    if usable < 90_000_000_000:
        raise ValueError(
            "Need at least 210 seconds for three temporal splits with 60-second guards"
        )
    train_end = start + int(usable * 0.4)
    calibration_start = train_end + 60_000_000_000
    calibration_end = calibration_start + int(usable * 0.25)
    return [
        ("TRAIN_DEV", start, train_end),
        ("CALIBRATION", calibration_start, calibration_end),
        ("TEST", calibration_end + 60_000_000_000, end),
    ]


def prepare(root, dataset_id="SENTINEL_FIRST_PERSON_V1"):
    raw = root / "raw"
    videos = discover(raw)
    if not videos:
        print(json.dumps({"status": "DATA_PENDING", "videos": 0}))
        return
    for path in videos:
        ignored = subprocess.run(["git", "check-ignore", "--quiet", str(path)], check=False)
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)], capture_output=True, check=False
        )
        if ignored.returncode != 0 or tracked.returncode == 0:
            raise ValueError("Raw media must be untracked and gitignored")
    output = root / "manifests" / "manifest.draft.json"
    if output.exists() or (root / "manifest.draft.json").exists():
        raise ValueError("Dataset already prepared; preserve its frozen split")
    policy = {
        "base_fps": 2,
        "review_spacing_ns": 3_000_000_000,
        "guard_ns": 60_000_000_000,
        "split_fractions": [0.4, 0.25, 0.35],
        "seed": 0,
        "near_duplicate": "8x8 average hash, Hamming <= 3",
        "selection": "2Hz PTS grid; >=3s review spacing; no detector-based selection",
    }
    manifest = {
        "schema_version": 2,
        "dataset": dataset_id,
        "scope": "SENTINEL_REAL_WORLD",
        "annotation_sha256": "0" * 64,
        "sequences": [],
        "images": [],
    }
    inventory = []
    prior_hashes = []
    media_seen = set()
    for path in videos:
        digest = file_hash(path)
        if digest in media_seen:
            raise ValueError("Duplicate media")
        media_seen.add(digest)
        pts = []
        with av.open(
            str(path),
            options={"protocol_whitelist": "file", "format_whitelist": "mov,matroska,webm,avi"},
        ) as container:
            stream = container.streams.video[0]
            stream.codec_context.thread_count = 1
            metadata = {
                "filename": path.name,
                "sha256": digest,
                "bytes": path.stat().st_size,
                "codec": stream.codec_context.name,
                "width": stream.width,
                "height": stream.height,
                "time_base": str(stream.time_base),
                "nominal_fps": str(stream.average_rate),
                "container_frame_count": stream.frames,
                "rotation_metadata": stream.metadata.get("rotate"),
                "source_type": "USER_OWNED_FIRST_PERSON",
                "ownership": "USER_DECLARED",
                "redistribution": "NOT_PLANNED",
            }
            for frame in container.decode(stream):
                if frame.pts is None or frame.time_base is None:
                    raise ValueError("Missing authoritative media PTS")
                time = int(frame.pts * frame.time_base * 1_000_000_000)
                if time < 0 or (pts and time <= pts[-1]):
                    raise ValueError("Nonmonotonic PTS")
                if frame.rotation != 0:
                    raise ValueError(
                        "Nonzero display rotation requires explicit orientation policy"
                    )
                pts.append(time)
                if len(pts) > 300_000:
                    raise ValueError("Recording exceeds bounded preparation limit of 300000 frames")
            if len(pts) < 2:
                raise ValueError("Insufficient decoded frames")
        end = pts[-1] + pts[-1] - pts[-2]
        metadata.update(
            decoded_frames=len(pts),
            start_ns=pts[0],
            end_ns=end,
            duration_seconds=(end - pts[0]) / 1e9,
            pts_status="STRICTLY_INCREASING",
            display_rotation=0,
        )
        inventory.append(metadata)
        segments = windows(pts[0], end)
        sequence_ids = {}
        for split, begin, finish in segments:
            sequence = digest[:16] + "-" + split.lower()
            sequence_ids[split] = sequence
            manifest["sequences"].append(
                {
                    "sequence_id": sequence,
                    "media_sha256": digest,
                    "parent_video_id": digest,
                    "start_ns": begin,
                    "end_ns": finish,
                    "source_url_or_reference": "USER_OWNED; media PTS, not sensor exposure",
                    "license_reference": "USER_DECLARED_LOCAL_R&D_ONLY",
                    "permission_status": "APPROVED_FOR_LOCAL_EVALUATION",
                    "sampling_fps": 2.0,
                    "sampling_policy": json.dumps(policy, sort_keys=True),
                }
            )
        last_selected = dict.fromkeys(sequence_ids, -(10**18))
        deadlines = {split: begin for split, begin, _ in segments}
        with av.open(
            str(path),
            options={"protocol_whitelist": "file", "format_whitelist": "mov,matroska,webm,avi"},
        ) as container:
            container.streams.video[0].codec_context.thread_count = 1
            for index, frame in enumerate(container.decode(video=0)):
                time = pts[index]
                selected = next(
                    (split for split, begin, finish in segments if begin <= time < finish), None
                )
                if selected is None or time < deadlines[selected]:
                    continue
                deadlines[selected] += (
                    (time - deadlines[selected]) // 500_000_000 + 1
                ) * 500_000_000
                if time - last_selected[selected] < policy["review_spacing_ns"]:
                    continue
                small = frame.reformat(width=8, height=8, format="gray").to_ndarray()
                signature = small.reshape(-1) > small.mean()
                if any(np.count_nonzero(signature != other) <= 3 for other in prior_hashes):
                    continue
                if len(prior_hashes) >= 1000:
                    raise ValueError("Review set exceeds 1000 frames; prepare a separate version")
                prior_hashes.append(signature)
                last_selected[selected] = time
                image_id = sequence_ids[selected] + f"-{index:06d}"
                destination = root / "sampled_frames" / (image_id + ".jpg")
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as stream:
                    frame.to_image().save(stream, format="JPEG", quality=95)
                manifest["images"].append(
                    {
                        "image_id": image_id,
                        "sequence_id": sequence_ids[selected],
                        "split": selected,
                        "observation_ns": time,
                        "path": "../sampled_frames/" + destination.name,
                        "sha256": file_hash(destination),
                        "width": frame.width,
                        "height": frame.height,
                        "coordinate_space": "ORIGINAL_CAMERA_CONTINUOUS_EDGES",
                        "annotations_reviewed": False,
                        "metadata": dict.fromkeys(
                            (
                                "lighting",
                                "motion",
                                "occlusion",
                                "environment",
                                "blur",
                                "provenance",
                            ),
                            "UNKNOWN",
                        ),
                        "annotations": [],
                    }
                )
        if file_hash(path) != digest:
            raise ValueError("Source changed during preparation")
    # Manifest lives at dataset root so all media paths are contained, never ../ escapes.
    for entry in manifest["images"]:
        entry["path"] = entry["path"].removeprefix("../")
    EvaluationDataset.model_validate_json(json.dumps(manifest))
    output.parent.mkdir(parents=True, exist_ok=True)
    # Operational inventory is private and gitignored, including local filenames.
    (root / "manifests" / "inventory.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "dataset_id": dataset_id,
                "configuration": policy,
                "configuration_hash": canonical_hash(policy),
                "annotation_version": "DRAFT-0",
                "sources": inventory,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "manifest.draft.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    output.write_text(
        json.dumps({"status": "DRAFT_NOT_GROUND_TRUTH", "manifest": "../manifest.draft.json"})
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "videos": len(videos),
                "frames": len(manifest["images"]),
                "status": "ANNOTATION_PENDING",
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("datasets/sentinel_first_person_v1"))
    parser.add_argument("--dataset-id", default="SENTINEL_FIRST_PERSON_V1")
    args = parser.parse_args()
    prepare(args.root, args.dataset_id)
