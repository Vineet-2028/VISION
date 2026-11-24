"""Full Guardian on a reproducible transformed local clip. No raw media is stored."""

import argparse
import json
from collections import Counter
from fractions import Fraction
from math import cos, radians, sin
from pathlib import Path
from time import perf_counter_ns

import av
import cv2
import numpy as np
from rescue_runtime import activate_onnx
from v0_replay import digest, run

from perception_lab.camera_orientation import CameraOrientationState
from perception_lab.contracts import Frame, FrameIdentity, PixelFormat, TimingProvenance
from perception_lab.sources import pts_to_ns


class RotatedClip:
    """Fixed sensor canvas, uniform fit and black padding, explicit synthetic metadata."""

    def __init__(self, path, source_id, max_pixels, start_ns, degrees, seconds, condition):
        self.path, self.source_id, self.max_pixels = path, source_id, max_pixels
        self.start_ns, self.degrees = start_ns, degrees
        self.seconds, self.condition = seconds, condition
        self.source_stamps = []

    def __iter__(self):
        with (
            self.path.open("rb") as f,
            av.open(
                f, options={"format_whitelist": "mov", "protocol_whitelist": "file"}
            ) as container,
        ):
            stream = container.streams.video[0]
            stream.codec_context.thread_count = 1
            container.seek(int(Fraction(self.start_ns, 10**9) / stream.time_base), stream=stream)
            for native in container.decode(stream):
                pts = pts_to_ns(native.pts, native.time_base)
                if native.is_corrupt or pts is None:
                    raise ValueError("Invalid source frame")
                if pts < self.start_ns:
                    continue
                if pts >= self.start_ns + self.seconds * 10**9:
                    return
                w, h = native.width, native.height
                if w * h > self.max_pixels:
                    raise ValueError("Frame exceeds pixel budget")
                started = perf_counter_ns()
                image = native.to_ndarray(format="rgb24")
                completed = perf_counter_ns()
                # Positive angle is clockwise in the received-image convention.
                a = radians(self.degrees)
                scale = min(
                    w / (w * abs(cos(a)) + h * abs(sin(a))), h / (w * abs(sin(a)) + h * abs(cos(a)))
                )
                mat = cv2.getRotationMatrix2D(((w - 1) / 2, (h - 1) / 2), -self.degrees, scale)
                pixels = cv2.warpAffine(image, mat, (w, h))
                if self.condition == "SYNTHETIC_LOW_LIGHT":
                    pixels = cv2.convertScaleAbs(pixels, alpha=0.12)
                elif self.condition == "SYNTHETIC_IMAGE_PAN":
                    phase = (pts - self.start_ns) / (self.seconds * 10**9)
                    shift = w * 0.12 * (2 * phase - 1)
                    pixels = cv2.warpAffine(
                        pixels, np.array([[1, 0, shift], [0, 1, 0]], dtype=np.float32), (w, h)
                    )
                elif self.condition == "SYNTHETIC_MOTION_BLUR":
                    pixels = cv2.blur(pixels, (15, 1))
                identity = FrameIdentity(
                    self.source_id,
                    len(self.source_stamps),
                    pts - self.start_ns,
                    TimingProvenance.AUTHORITATIVE_PTS,
                )
                orientation = CameraOrientationState(
                    identity,
                    None,
                    "GOOD",
                    "SYNTHETIC_TEST",
                    "known injected clockwise image roll",
                    roll_radians=a if self.degrees <= 180 else a - 2 * radians(180),
                )
                self.source_stamps.append(pts)
                yield Frame(
                    identity,
                    pixels,
                    PixelFormat.RGB,
                    started,
                    completed,
                    camera_orientation=orientation,
                )

    def close(self):
        pass  # The iterator owns both context managers.


def evaluate(args):
    args.output.mkdir(parents=True, exist_ok=False)
    raw = json.loads(args.config.read_text())
    if (
        not raw.get("detector")
        or not raw.get("segmentation")
        or (raw.get("motion") or {}).get("flow_provider") != "lk"
    ):
        raise ValueError("Rotated suite requires full Guardian configuration")
    raw.update(realtime_rescue=False, orientation_canonicalization=args.correction)
    for name in ("input", "calibration", "entity_semantics_ontology"):
        raw[name] = str((args.config.parent / raw[name]).resolve(strict=True))
    for name in ("detector", "segmentation"):
        raw[name]["weights"] = str((args.config.parent / raw[name]["weights"]).resolve(strict=True))
    config = args.output / "clip-config.json"
    config.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    clip = RotatedClip(
        Path(raw["input"]),
        raw["source_id"],
        raw["max_pixels"],
        args.start_ns,
        args.degrees,
        args.seconds,
        args.condition,
    )
    _, handles = activate_onnx(args.ort_runtime, args.cuda_libraries, args.cudnn_directory)
    try:
        run(
            config,
            args.output / "replay",
            "OFFLINE_REPLAY",
            args.seconds,
            source_factory=lambda *_: clip,
        )
    finally:
        for handle in handles:
            handle.close()
    manifest = json.loads((args.output / "replay/manifest.json").read_text())
    counts = manifest["session"]["summary"]["frame_counts"]
    if (
        counts["processed"] != 30 * args.seconds
        or counts["failed"]
        or counts["dropped"]
        or len(clip.source_stamps) != counts["processed"]
    ):
        raise ValueError("Incomplete rotated clip")
    stages, view, levels = Counter(), Counter(), Counter()
    with (args.output / "replay/updates.jsonl").open(encoding="utf-8") as trace:
        for index, line in enumerate(trace):
            row = json.loads(line)
            if row["identity"]["observation_ns"] != clip.source_stamps[index] - args.start_ns:
                raise ValueError("Transformed source identity mismatch")
            if row["camera_orientation"]["identity"] != row["identity"]:
                raise ValueError("Orientation lost source provenance")
            view[row["camera_view_quality"]["status"]] += 1
            for stage, items in (
                ("detector", "detections"),
                ("tracks", "tracks"),
                ("world", "entities"),
                ("corridor_analysis", "entity_relations"),
                ("trajectory_set", "trajectories"),
                ("interaction_analysis", "entity_interactions"),
                ("risk_assessment_set", "assessments"),
                ("attention_decision_set", "selected"),
            ):
                stages[stage] += len((row[stage] or {}).get(items, []))
            for alert in (row["alert_output_set"] or {}).get("outputs", []):
                if alert["delivered"]:
                    if (
                        row["camera_view_quality"]["status"] == "UNUSABLE"
                        or alert["delivery_timestamp"] >= alert["intent"]["valid_until_ns"]
                    ):
                        raise ValueError("Invalid alert on transformed clip")
                    levels[alert["presentation"]["semantic_level"]] += 1
    if sum(view.values()) != counts["processed"]:
        raise ValueError("Rotated trace row count mismatch")
    report = {
        "input_profile_sha256": digest(args.config),
        "injection_source_sha256": digest(Path(__file__)),
        "source_pts_ns": clip.source_stamps,
        "degrees_clockwise": args.degrees,
        "correction": args.correction,
        "condition": args.condition,
        "frame_counts": counts,
        "stage_item_counts": stages,
        "view_status": view,
        "text_sink_acceptances_by_level": levels,
        "injection_canvas": "FIT_ORIGINAL_SIZE_BLACK_PADDING",
        "physical_calibration": "UNMEASURED",
        "metadata_provenance": "SYNTHETIC_TEST",
    }
    (args.output / "qualification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "output", "ort-runtime", "cuda-libraries", "cudnn-directory"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--start-ns", type=int, required=True)
    parser.add_argument("--seconds", type=int, choices=range(1, 7), default=2)
    parser.add_argument(
        "--degrees", type=int, choices=(0, 90, 180, 270, 30, -30, 45, -45), required=True
    )
    parser.add_argument(
        "--condition",
        choices=("SOURCE", "SYNTHETIC_LOW_LIGHT", "SYNTHETIC_IMAGE_PAN", "SYNTHETIC_MOTION_BLUR"),
        default="SOURCE",
    )
    parser.add_argument("--correction", action="store_true")
    args = parser.parse_args()
    if args.start_ns < 0:
        parser.error("Clip offset must be nonnegative")
    evaluate(args)
