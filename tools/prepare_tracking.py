"""Prepare local, human-reviewable track proposals. Never automatically approve IDs."""

import argparse
import json
import re
import subprocess
from dataclasses import asdict
from pathlib import Path

import av
import numpy as np

from perception_lab.config import (
    Calibration,
    DetectorConfig,
    PreprocessConfig,
    read_json,
)
from perception_lab.contracts import Frame, FrameIdentity, PixelFormat, TimingProvenance
from perception_lab.detector_runtime import file_hash
from perception_lab.edge_runtime import PicoDetDetector, YoloXDetector
from perception_lab.geometry import CoreGeometry
from perception_lab.preprocessing import BasicPreprocessor
from perception_lab.tracking import AssociationTracker
from perception_lab.tracking_config import TrackerConfig
from perception_lab.tracking_dataset import TrackingDataset, validate_review
from perception_lab.tracking_types import DetectorEvidence


def prepare(args):
    if args.output.exists():
        raise ValueError("Output exists; use a new dataset version")
    if not 5 <= args.fps <= 10 or not 20 <= args.duration <= 45 or not 3 <= len(args.starts) <= 5:
        raise ValueError("Use 3..5 clips, 20..45 seconds, 5..10 FPS")
    if len(args.starts) * args.duration * args.fps > 2500 or any(s < 0 for s in args.starts):
        raise ValueError("Review budget or timestamp invalid")
    if any(
        b < a + args.duration
        for a, b in zip(sorted(args.starts), sorted(args.starts)[1:], strict=False)
    ):
        raise ValueError("Overlapping clips")
    if subprocess.run(["git", "check-ignore", "--quiet", str(args.video)], check=False).returncode:
        raise ValueError("Raw video must be ignored")
    source_hash = file_hash(args.video)
    config = read_json(args.config)
    d = DetectorConfig.model_validate(config["detector"])
    factory = {"picodet": PicoDetDetector, "yolox": YoloXDetector}[d.runtime]
    detector = factory(
        args.config.parent / d.weights,
        d.sha256,
        size=d.input_size,
        confidence=0.1,
        threads=1,
    )
    calibration = Calibration.model_validate(read_json(args.config.parent / config["calibration"]))
    geometry = CoreGeometry(calibration)
    preprocessor = BasicPreprocessor(geometry, PreprocessConfig())
    args.output.mkdir(parents=True)
    (args.output / "frames").mkdir()
    frames, predictions = [], []
    for index, start in enumerate(args.starts):
        clip = f"clip-{index + 1}"
        tracker = AssociationTracker(
            TrackerConfig(),
            clip,
            clip,
            calibration.resolution.width,
            calibration.resolution.height,
        )
        due, end, sequence = (
            start * 1_000_000_000,
            (start + args.duration) * 1_000_000_000,
            0,
        )
        with av.open(
            str(args.video),
            options={
                "protocol_whitelist": "file",
                "format_whitelist": "mov,matroska,avi",
            },
        ) as container:
            container.seek(start * 1_000_000, backward=True)
            for decoded in container.decode(video=0):
                if decoded.pts is None or decoded.time_base is None:
                    raise ValueError("Authoritative PTS required")
                timestamp = int(decoded.pts * decoded.time_base * 1_000_000_000)
                if timestamp < due:
                    continue
                if timestamp >= end:
                    break
                due = (
                    start * 1_000_000_000
                    + ((timestamp - start * 1_000_000_000) * args.fps // 1_000_000_000 + 1)
                    * 1_000_000_000
                    // args.fps
                )
                identity = FrameIdentity(
                    clip, sequence, timestamp, TimingProvenance.AUTHORITATIVE_PTS
                )
                frame = Frame(
                    identity,
                    np.ascontiguousarray(decoded.to_ndarray(format="rgb24")),
                    PixelFormat.RGB,
                    0,
                    0,
                )
                batch = detector.detect(preprocessor.prepare(frame), identity)
                result = tracker.update(
                    clip,
                    identity,
                    DetectorEvidence.SUCCESS
                    if batch.detections
                    else DetectorEvidence.SUCCESS_EMPTY,
                    batch,
                )
                name = f"{clip}-{sequence:04}.jpg"
                decoded.to_image().save(args.output / "frames" / name, quality=92)
                annotations = []
                for track in result.tracks:
                    if track.observation_status != "OBSERVED":
                        continue
                    b = track.latest_observed_bbox
                    box = [
                        max(0, b.x1),
                        max(0, b.y1),
                        min(frame.width, b.x2),
                        min(frame.height, b.y2),
                    ]
                    if box[2] <= box[0] or box[3] <= box[1]:
                        continue
                    annotations.append(
                        {
                            "ground_truth_track_id": str(track.track_id.serial),
                            "label": track.history[-1].category.value,
                            "box": box,
                        }
                    )
                frames.append(
                    {
                        "image_id": name[:-4],
                        "clip_id": clip,
                        "observation_ns": timestamp,
                        "path": "frames/" + name,
                        "sha256": file_hash(args.output / "frames" / name),
                        "width": frame.width,
                        "height": frame.height,
                        "annotations": annotations,
                    }
                )
                predictions.append({"image_id": name[:-4], "batch": asdict(batch)})
                sequence += 1
        tracker.close()
        if sequence < args.fps * args.duration - 1:
            raise ValueError("Clip ended early")
        print(json.dumps({"clip": clip, "frames": sequence}), flush=True)
    if file_hash(args.video) != source_hash:
        raise ValueError("Source changed")
    data = TrackingDataset.model_validate_json(
        json.dumps(
            {
                "dataset": "SENTINEL_TRACKING_V1",
                "source_sha256": source_hash,
                "sampling_fps": args.fps,
                "frames": frames,
            }
        )
    )
    (args.output / "draft.json").write_text(data.model_dump_json(indent=2), encoding="utf-8")
    (args.output / "predictions.json").write_text(json.dumps(predictions), encoding="utf-8")
    template = Path("tools/track-review.html").read_text(encoding="utf-8")
    (args.output / "review.html").write_text(
        re.sub(
            r"/\*SENTINEL_DATA\*/\s*null",
            lambda _: data.model_dump_json().replace("<", "\\u003c"),
            template,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "frames": len(frames),
                "status": "HUMAN_TRACK_GROUND_TRUTH_REVIEW_REQUIRED",
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--video", type=Path, required=True)
    prep.add_argument("--config", type=Path, required=True)
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--starts", type=int, nargs="+", required=True)
    prep.add_argument("--duration", type=int, default=20)
    prep.add_argument("--fps", type=int, default=5)
    review = commands.add_parser("validate-review")
    review.add_argument("--draft", type=Path, required=True)
    review.add_argument("--review", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args)
    else:
        reviewed = validate_review(args.draft, args.review)
        print(
            json.dumps(
                {
                    "reviewed_frames": len(reviewed.frames),
                    "review_sha256": file_hash(args.review),
                }
            )
        )
