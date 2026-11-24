"""Same-frame rescued PicoDet settings; separate CPU screening artifact."""

import argparse
import json
from pathlib import Path
from time import perf_counter_ns

import av
from v0_analyze import quantiles
from v02_candidate_population import digest, exact_frame, source_targets

from perception_lab.config import Calibration, PreprocessConfig
from perception_lab.contracts import Frame, FrameIdentity, PixelFormat, TimingProvenance
from perception_lab.edge_runtime import PicoDetDetector
from perception_lab.geometry import CoreGeometry
from perception_lab.offline import enforce_offline
from perception_lab.preprocessing import BasicPreprocessor


def main():
    import psutil

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    population_path = root / "benchmark-results/v02/populations-02.json"
    population = json.loads(population_path.read_text())
    targets = source_targets(population)
    config = json.loads(
        (
            root / "benchmark-results/v0-rescue/realtime-06-gpu-no-depth/configuration.json"
        ).read_text()
    )
    video = Path(config["input"])
    if digest(video) != population["source_sha256"]:
        raise ValueError("Source mismatch")
    args.output.mkdir(parents=True, exist_ok=False)
    enforce_offline()
    detector = PicoDetDetector(
        Path(config["detector"]["weights"]),
        config["detector"]["sha256"],
        confidence=0.1,
        device="cpu",
        threads=2,
    )
    geometry = CoreGeometry(
        Calibration.model_validate_json(Path(config["calibration"]).read_text())
    )
    preprocess = BasicPreprocessor(geometry, PreprocessConfig())
    durations, rss = [], []
    process = psutil.Process()
    with (
        video.open("rb") as source,
        av.open(
            source, options={"format_whitelist": "mov", "protocol_whitelist": "file"}
        ) as container,
        (args.output / "predictions.jsonl").open("x") as sink,
    ):
        stream = container.streams.video[0]
        stream.codec_context.thread_count = 1
        for index, timestamp in enumerate(targets):
            image = exact_frame(container, stream, timestamp)[:, :, ::-1].copy()
            now = perf_counter_ns()
            frame = Frame(
                FrameIdentity(
                    config["source_id"], index, timestamp, TimingProvenance.AUTHORITATIVE_PTS
                ),
                image,
                PixelFormat.RGB,
                now,
                now,
            )
            prepared = preprocess.prepare(frame)
            if index == 0:
                detector.detect(prepared, frame.identity)
            start = perf_counter_ns()
            batch = detector.detect(prepared, frame.identity)
            elapsed = perf_counter_ns() - start
            durations.append(elapsed)
            rss.append(process.memory_info().rss)
            regions = [
                {
                    "box": list(d.box.coordinates),
                    "concept": d.class_name if d.label.value != "UNKNOWN" else None,
                    "confidence": d.confidence,
                    "confidence_basis": "JOINT_DETECTION_SCORE",
                }
                for d in batch.detections
            ]
            sink.write(
                json.dumps(
                    {
                        "source_ns": timestamp,
                        "regions": regions,
                        "call_ns": elapsed,
                        "rss_bytes": rss[-1],
                    }
                )
                + "\n"
            )
            if (index + 1) % 30 == 0:
                print(f"PicoDet: {index + 1}/{len(targets)}", flush=True)
    report = {
        "status": "COMPLETE_CPU_SCREENING_NOT_RUNTIME_QUALIFICATION",
        "model": "rescued-picodet-s",
        "source_sha256": population["source_sha256"],
        "model_sha256": config["detector"]["sha256"],
        "population_sha256": digest(population_path),
        "predictions_sha256": digest(args.output / "predictions.jsonl"),
        "frames": len(targets),
        "call_time": quantiles(durations),
        "runtime": detector.runtime_metadata,
        "max_sampled_rss_bytes": max(rss),
        "vram_bytes": None,
        "adopted": False,
        "baseline_deployed_alert_text": "60 Object. outputs; names not authorized for speech",
        "scope": "CPU same-frame detector proxy; not a reproduction of realtime cadence",
    }
    (args.output / "summary.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
