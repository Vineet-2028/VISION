"""Offline single-frame research smoke test, not an accuracy benchmark."""

import argparse
import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path
from time import perf_counter_ns

from perception_lab.config import canonical_hash
from perception_lab.contracts import Frame
from perception_lab.offline import enforce_offline
from perception_lab.sources import VideoFileSource


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    registry = json.loads((root / "configs/perception/research-models-v02.json").read_text())
    record = next(model for model in registry["models"] if model["id"] == args.model)
    weights = root / "benchmark-results/v02/models" / record["filename"]
    with weights.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != record["sha256"]:
            raise ValueError("Research checkpoint hash mismatch")
    args.output.mkdir(parents=True, exist_ok=False)
    settings_dir = args.output.resolve() / "vendor-settings"
    settings_dir.mkdir()
    os.environ["YOLO_CONFIG_DIR"] = str(settings_dir)
    os.environ["YOLO_AUTOINSTALL"] = "false"
    os.environ["YOLO_OFFLINE"] = "true"
    enforce_offline()
    import torch
    from ultralytics import YOLO, settings

    from perception_lab.concept_resolver import HierarchyConceptResolver
    from perception_lab.detection import Box
    from perception_lab.entity_adapter import JointScoreEntityAdapter, ProviderRegion

    settings.update({"sync": False})
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    source = VideoFileSource(args.video, "v02-single-frame-smoke", 4096 * 4096)
    source.realtime_minimum_ns = lambda: 37_000_000_000
    try:
        frame = next(item for item in source if isinstance(item, Frame))
    finally:
        source.close()
    image = frame.pixels[:, :, ::-1].copy()  # RGB source to vendor BGR ndarray boundary.
    model = YOLO(str(weights))
    durations = []
    result = None
    for repetition in range(6):
        started = perf_counter_ns()
        result = model.predict(
            image,
            imgsz=640,
            device="cpu",
            half=False,
            conf=0.05,
            max_det=100,
            verbose=False,
            save=False,
            stream=False,
        )[0]
        elapsed = perf_counter_ns() - started
        if repetition:
            durations.append(elapsed)
    assert result is not None and result.boxes is not None
    regions = tuple(
        ProviderRegion(Box(*map(float, coordinates)), float(score), int(index))
        for coordinates, score, index in zip(
            result.boxes.xyxy.tolist(),
            result.boxes.conf.tolist(),
            result.boxes.cls.tolist(),
            strict=True,
        )
    )
    adapter = JointScoreEntityAdapter(
        record["id"],
        record["sha256"],
        record["id"] + "-embedded",
        "v8.4.0",
        result.names,
        HierarchyConceptResolver(root / "configs/perception/ontology/vision-domain-v1.json"),
    )
    observations = adapter.convert(
        frame.identity,
        regions,
        canonical_hash(
            {
                "operation": "identity",
                "width": frame.width,
                "height": frame.height,
                "basis": "original-camera-edges",
            }
        ),
    )
    with args.video.open("rb") as stream:
        video_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    report = {
        "scope": "SINGLE_FRAME_REPEATED_CPU_SMOKE_NOT_ACCURACY_OR_REALTIME_BENCHMARK",
        "model": record["id"],
        "sha256": record["sha256"],
        "video_sha256": video_hash,
        "runtime": "torch CPU FP32; 2 intra-op threads; Python network denied",
        "source_frame": asdict(frame.identity),
        "source_dimensions": [frame.width, frame.height],
        "warmup_calls": 1,
        "measured_calls": len(durations),
        "end_to_end_call_ms": [value / 1e6 for value in durations],
        "vocabulary_size": len(result.names),
        "observations": [asdict(item) for item in observations],
        "mask_policy": "not retained; boxes only in this probe",
        "license_decision": record["license_decision"],
        "accuracy_measured": False,
        "product_adopted": False,
    }
    (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps({key: value for key, value in report.items() if key != "observations"}, indent=2)
    )
    print(f"observations={len(observations)}")


if __name__ == "__main__":
    main()
