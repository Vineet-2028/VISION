"""Verify and replay exact saved input bytes/metadata independently of neural recomputation."""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from perception_lab.field_protocol import check_camera_jpeg


def recompute_detector(case: Path, index: dict, frames: list) -> dict:
    """Keep native model/JVM allocation in a bounded, disposable child process."""
    expected = "ecd83215cc8f8e144ec9126b61415e8ca38b854a4126cfdbc6e52d55affa6254"
    if index["gateway_manifest"].get("configuration_hash") != expected:
        raise ValueError("Recorded release identity unavailable or mismatched")
    with tempfile.TemporaryDirectory(prefix="vision-detector-replay-") as directory:
        output = Path(directory) / "result.json"
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--case",
                str(case.resolve()),
                "--output",
                str(output),
                "--isolated-worker",
            ],
            check=True,
            timeout=180,
        )
        result = json.loads(output.read_text())
        for target, source in zip(frames, result["frames"], strict=True):
            if (target["sequence"], target["camera_ns"], target["jpeg_sha256"]) != (
                source["sequence"],
                source["camera_ns"],
                source["jpeg_sha256"],
            ):
                raise ValueError("Worker input identity mismatch")
            target["recomputed_output"] = source["recomputed_output"]
        return result["recomputation_provenance"]


def _recompute_detector(case: Path, index: dict, frames: list) -> dict:
    """CPU-only cold-start detector comparison, not a replay of temporal decisions."""
    from time import perf_counter_ns

    import cv2
    import numpy as np
    import psutil
    from alpha_field_gateway import hash_file, release_profile
    from alpha_trace import compact_alpha

    from perception_lab.config import Calibration, LabConfig
    from perception_lab.contracts import Frame, FrameIdentity, PixelFormat, TimingProvenance
    from perception_lab.field_detector_diagnostics import DiagnosticPicoDet
    from perception_lab.field_orientation import field_orientation
    from perception_lab.field_protocol import FrameHeader
    from perception_lab.geometry import CoreGeometry
    from perception_lab.orientation_preprocessing import build_preprocessor

    manifest = Path(__file__).resolve().parents[1] / (
        "benchmark-results/v02/VISION_CONTROLLED_ALPHA_V1/manifest.json"
    )
    expected = "ecd83215cc8f8e144ec9126b61415e8ca38b854a4126cfdbc6e52d55affa6254"
    if hash_file(manifest) != expected:
        raise ValueError("Frozen release manifest mismatch")
    if index["gateway_manifest"].get("configuration_hash") != expected:
        raise ValueError("Recorded release identity unavailable or mismatched")
    if psutil.virtual_memory().available < 3 * 1024**3:
        raise RuntimeError("At least 3 GiB free RAM required for detector replay")
    config = LabConfig.model_validate(release_profile(manifest))
    detector_config = config.detector
    options = dict(confidence=detector_config.confidence, device="cpu", threads=1)
    startup_rss = psutil.Process().memory_info().rss
    candidate = DiagnosticPicoDet(Path(detector_config.weights), detector_config.sha256, **options)
    observer_session = candidate.session
    origin = int(frames[0]["camera_ns"])
    for position, record in enumerate(frames):
        if psutil.virtual_memory().available < 2 * 1024**3:
            raise RuntimeError("2 GiB RAM reserve reached; replay incomplete")
        packet = json.loads((case / f"{position}.json").read_text())
        admitted = [e for e in packet["recorded_events"] if e.get("kind") == "FRAME_ADMITTED"]
        if len(admitted) != 1 or packet["correspondence"] != "EXACT_ADMITTED_CAPTURE":
            raise ValueError("Exact admitted capture required for recomputation")
        if admitted[0].get("rotation") != packet["rotation"]:
            raise ValueError("Recorded orientation unavailable or mismatched")
        image = (case / f"{position}.jpg").read_bytes()
        if hashlib.sha256(image).hexdigest() != packet["jpeg_sha256"]:
            raise ValueError("Replay image changed during recomputation")
        pixels = cv2.imdecode(
            np.frombuffer(image, np.uint8), cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION
        )
        if pixels is None or pixels.shape != (packet["height"], packet["width"], 3):
            raise ValueError("Decoded capture dimensions mismatch")
        cal = json.loads(Path(config.calibration).read_text())
        if cal["calibration_quality"]["state"] != "UNKNOWN":
            raise ValueError("Cannot transplant physical camera calibration")
        cal.update(
            camera_id="field-camera",
            resolution={"width": packet["width"], "height": packet["height"]},
        )
        geometry = CoreGeometry(Calibration.model_validate(cal))
        identity = FrameIdentity(
            index["session_id"],
            packet["sequence"],
            int(packet["camera_ns"]) - origin,
            TimingProvenance.AUTHORITATIVE_PTS,
        )
        header = FrameHeader.model_validate(
            dict(
                protocol_version="VISION_FIELD_PROTOCOL_V1",
                session_id=index["session_id"],
                sequence=packet["sequence"],
                camera_ns=packet["camera_ns"],
                capture_ns=packet["camera_ns"],
                send_ns=packet["camera_ns"],
                sync_version=1,
                rotation=packet["rotation"],
                width=packet["width"],
                height=packet["height"],
                format="JPEG",
                jpeg_quality=75,
                sensors=admitted[0].get("sensors"),
            )
        )
        frame = Frame(
            identity,
            pixels,
            PixelFormat.BGR,
            0,
            0,
            camera_orientation=field_orientation(identity, header),
        )
        start = perf_counter_ns()
        prepared = build_preprocessor(geometry, config).prepare(frame)
        preprocessing_ns = perf_counter_ns() - start
        candidate.session = observer_session.session
        start = perf_counter_ns()
        # Call the frozen adapter directly: same native session, no observer allocation.
        original = super(DiagnosticPicoDet, candidate).detect(prepared, identity)
        baseline_ns = perf_counter_ns() - start
        baseline_stages = dict(candidate.last_timings_ns)
        candidate.session = observer_session
        start = perf_counter_ns()
        observed = candidate.detect(prepared, identity)
        candidate_ns = perf_counter_ns() - start
        parity = (
            original.detections == observed.detections
            and original.transform_hash == observed.transform_hash
        )
        if not parity:
            raise ValueError("Diagnostic observer changed detector outputs")
        record["recomputed_output"] = {
            "scope": "COLD_START_DETECTOR_ONLY_CPU",
            "detector_parity": parity,
            "detections": compact_alpha(observed.detections),
            "diagnostics": candidate.diagnostic,
            "baseline_ns": baseline_ns,
            "candidate_ns": candidate_ns,
            "preprocessing_ns": preprocessing_ns,
            "baseline_stages_ns": baseline_stages,
            "candidate_stages_ns": dict(candidate.last_timings_ns),
            "observer_elapsed_delta_ns": candidate_ns - baseline_ns,
        }
    return {
        "model_sha256": detector_config.sha256,
        "release_sha256": expected,
        "startup_rss_bytes": startup_rss,
        "peak_rss_bytes": getattr(psutil.Process().memory_info(), "peak_wset", None),
        "model_instances": 1,
        "device": "CPU",
        "vram_allocated_by_model_bytes": 0,
        "configuration": {
            "confidence": detector_config.confidence,
            "threads": 1,
            "size": 416,
            "orientation_canonicalization": config.orientation_canonicalization,
        },
        "timing_limitations": "Paired CPU samples include warmup; not realtime qualification",
        "observation_clock": "Camera timestamps retained; detector clock rebased to clip start",
    }


def replay(
    case: Path, output: Path, recompute: bool = False, isolated_worker: bool = False
) -> None:
    if output.exists():
        raise FileExistsError(output)
    index_path = case / "index.json"
    if index_path.stat().st_size > 65536:
        raise ValueError("Oversized index")
    index = json.loads(index_path.read_text())
    if index.get("schema") != "vision.field.case.v1" or not 1 <= len(index["frames"]) <= 24:
        raise ValueError("Invalid case")
    frames = []
    digest = hashlib.sha256()
    previous = -1
    for position, reference in enumerate(index["frames"]):
        packet_path, image_path = case / f"{position}.json", case / f"{position}.jpg"
        if packet_path.stat().st_size > 2_000_000 or image_path.stat().st_size > 512_000:
            raise ValueError("Oversized frame")
        packet = json.loads(packet_path.read_text())
        image = image_path.read_bytes()
        if (
            packet["sequence"] != reference["sequence"]
            or packet["camera_ns"] != reference["camera_ns"]
            or int(packet["camera_ns"]) <= previous
            or hashlib.sha256(image).hexdigest() != packet["jpeg_sha256"]
        ):
            raise ValueError("Replay identity/checksum mismatch")
        check_camera_jpeg(image, packet["width"], packet["height"])
        previous = int(packet["camera_ns"])
        digest.update(image)
        frames.append(
            {
                "sequence": packet["sequence"],
                "camera_ns": packet["camera_ns"],
                "jpeg_sha256": packet["jpeg_sha256"],
                "rotation": packet["rotation"],
                "recorded_output": packet["recorded_events"],
                "recomputed_output": None,
            }
        )
    runner = _recompute_detector if isolated_worker else recompute_detector
    computation = runner(case, index, frames) if recompute else None
    result = {
        "schema": "vision.field.input-replay.v1",
        "session_id": index["session_id"],
        "status": "EXACT_CAPTURED_INPUT_VERIFIED",
        "input_bytes_sha256": digest.hexdigest(),
        "frames": frames,
        "neural_recomputation": "COLD_START_DETECTOR_ONLY_CPU" if recompute else "NOT_RUN",
        "recomputation_provenance": computation,
        "full_equivalence": "UNAVAILABLE",
        "missing_inputs": [
            "Complete pre-clip tracker/semantic/policy state",
            "Original inference scheduling and process state",
        ],
    }
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--recompute-detector", action="store_true")
    parser.add_argument("--isolated-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    replay(
        args.case,
        args.output,
        args.recompute_detector or args.isolated_worker,
        args.isolated_worker,
    )
