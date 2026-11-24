"""Compare upright, raw-rotated and corrected inputs through the same Guardian profile."""

import argparse
import json
import sys
from pathlib import Path

from alpha_candidate_isolate import supervise


def cases(review):
    images = review["images"]

    def densest(labels):
        def count(image):
            return sum(not box["ignore"] and box["label"] in labels for box in image["annotations"])

        image = max(images, key=count)
        if not image["annotations_reviewed"] or not count(image):
            raise ValueError("Missing reviewed class instances for the clip anchor")
        return image["observation_ns"]

    return [
        ("walking", 90, 5_000_000_000, "SOURCE"),
        ("person_density_proxy", 180, densest({"PERSON"}), "SOURCE"),
        ("two_wheeler_instances", 270, densest({"BICYCLE", "MOTORCYCLE"}), "SOURCE"),
        ("image_pan", 30, 30_000_000_000, "SYNTHETIC_IMAGE_PAN"),
        ("motion_blur", -30, 50_000_000_000, "SYNTHETIC_MOTION_BLUR"),
        ("darkened", 45, 15_000_000_000, "SYNTHETIC_LOW_LIGHT"),
        ("walking_second_window", -45, 90_000_000_000, "SOURCE"),
    ]


def evaluate(args):
    args.output.mkdir(parents=True, exist_ok=False)
    review = json.loads(args.annotations.read_text())
    config = json.loads(args.config.read_text())
    from v0_replay import digest

    video_hash = digest((args.config.parent / config["input"]).resolve())
    if {sequence["media_sha256"] for sequence in review["sequences"]} != {video_hash}:
        raise ValueError("Clip reference source mismatch")
    results = []
    for name, degrees, start, condition in cases(review):
        stamps = None
        for arm, angle, correction in (
            ("upright", 0, False),
            ("rotated", degrees, False),
            ("corrected", degrees, True),
        ):
            dest = args.output / f"{name}-{arm}"
            command = [sys.executable, str(Path(__file__).with_name("alpha_rotated_clip.py"))]
            for key in ("config", "ort_runtime", "cuda_libraries", "cudnn_directory"):
                command += ["--" + key.replace("_", "-"), str(getattr(args, key).resolve())]
            command += [
                "--output",
                str(dest),
                "--start-ns",
                str(start),
                "--degrees",
                str(angle),
                "--condition",
                condition,
            ]
            if correction:
                command.append("--correction")
            resource = supervise(
                command, dest.with_name(dest.name + "-process"), 120, gpu_probe=args.gpu_probe
            )
            if resource["status"] != "EXITED_SUCCESS":
                raise RuntimeError(f"Rotated suite stopped at {name}/{arm}: {resource['status']}")
            result = json.loads((dest / "qualification.json").read_text())
            if stamps is not None and stamps != result["source_pts_ns"]:
                raise ValueError("Rotated arms used different source frames")
            stamps = result["source_pts_ns"]
            results.append(dict(result, clip=name, arm=arm))
            print(f"{name}/{arm}: {len(stamps)} frames", flush=True)
    report = {
        "source_sha256": video_hash,
        "annotation_sha256": digest(args.annotations),
        "arms": results,
        "comparisons": compare(results),
        "scope": "Controlled image-plane perturbations on one recording with unmeasured pose.",
    }
    (args.output / "suite.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def compare(results):
    by_clip = {}
    for result in results:
        by_clip.setdefault(result["clip"], {})[result["arm"]] = result
    comparisons = {}
    for clip, arms in by_clip.items():
        upright = arms["upright"]["stage_item_counts"]
        comparisons[clip] = {
            key: {
                stage: arm["stage_item_counts"][stage] - count for stage, count in upright.items()
            }
            for key, arm in arms.items()
            if key != "upright"
        }
    return comparisons


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "config",
        "annotations",
        "output",
        "ort-runtime",
        "cuda-libraries",
        "cudnn-directory",
        "gpu-probe",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    evaluate(parser.parse_args())
