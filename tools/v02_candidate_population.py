"""All fixed-population source frames; bounded screening, not realtime qualification."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from time import perf_counter_ns

import av

from perception_lab.offline import enforce_offline
from perception_lab.sources import pts_to_ns


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_budget(now_ns, deadline_ns, available_ram):
    if now_ns >= deadline_ns:
        raise RuntimeError("Processing time cap reached; partial output is not qualification")
    if available_ram < 2 * 1024**3:
        raise RuntimeError("Less than 2 GiB system RAM available; stopping benchmark")


def source_targets(population):
    if len(population["alerts"]) != 60 or len(population["events"]) != 188:
        raise ValueError("Fixed population denominator mismatch")
    if (
        len({a["alert_id"] for a in population["alerts"]}) != 60
        or len({e["event_id"] for e in population["events"]}) != 188
    ):
        raise ValueError("Fixed population contains duplicated event identities")
    return sorted(
        {a["source_observation_ns"] for a in population["alerts"]}
        | {o["observation_ns"] for e in population["events"] for o in e["observations"]}
    )


def exact_frame(container, stream, timestamp):
    base = stream.time_base
    offset = timestamp * base.denominator // (base.numerator * 1_000_000_000)
    container.seek(offset, stream=stream, backward=True, any_frame=False)
    for native in container.decode(stream):
        actual = pts_to_ns(native.pts, native.time_base)
        if actual is None or actual < timestamp:
            continue
        if actual != timestamp or native.is_corrupt:
            raise ValueError(f"Exact source frame unavailable: {timestamp}, decoded {actual}")
        if native.width * native.height > 4096 * 4096:
            raise ValueError("Frame size limit")
        return native.to_ndarray(format="bgr24")
    raise ValueError("Source ended before required timestamp")


def residual_targets(population):
    if population.get("status") != "EXACT_LINEAGE_RESIDUAL_SCREENING_SET":
        raise ValueError("Exact-lineage residual set required")
    targets = population["targets"]
    if not 1 <= len(targets) <= 10_000 or len({t["alert_id"] for t in targets}) != len(targets):
        raise ValueError("Invalid residual alert identities/count")
    stamps = set()
    for target in targets:
        if not target["screenable"]:
            continue
        observation, lineage = target["source_observation"], target["lineage"]
        if (
            observation["observation_id"] != lineage["observation_id"]
            or observation["source_frame"] != lineage["origin_source_identity"]
        ):
            raise ValueError("Residual source lineage mismatch")
        stamp = observation["source_frame"]["observation_ns"]
        if type(stamp) is not int or stamp < 0:
            raise ValueError("Invalid residual timestamp")
        stamps.add(stamp)
    if not stamps:
        raise ValueError("No screenable source observations")
    return sorted(stamps)


def main():
    import psutil

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--torch-runtime", type=Path)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--max-run-minutes", type=int, default=10)
    parser.add_argument("--video", type=Path, required=True)
    population_options = parser.add_mutually_exclusive_group()
    population_options.add_argument(
        "--population",
        type=Path,
    )
    population_options.add_argument("--residual", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.warmup <= 20:
        raise ValueError("Warmup must be bounded between 1 and 20")
    if not 1 <= args.max_run_minutes <= 60:
        raise ValueError("Processing cap must be between 1 and 60 minutes")
    root = Path(__file__).resolve().parents[1]
    population_path = (
        args.residual or args.population or Path("benchmark-results/v02/populations-02.json")
    )
    population = json.loads(population_path.read_text())
    targets = residual_targets(population) if args.residual else source_targets(population)
    if digest(args.video) != population["source_sha256"]:
        raise ValueError("Source video hash mismatch")
    registry = json.loads((root / "configs/perception/research-models-v02.json").read_text())
    model_record = next(m for m in registry["models"] if m["id"] == args.model)
    weights = root / "benchmark-results/v02/models" / model_record["filename"]
    if digest(weights) != model_record["sha256"]:
        raise ValueError("Model hash mismatch")
    args.output.mkdir(parents=True, exist_ok=False)
    settings_path = args.output.resolve() / "vendor-settings"
    settings_path.mkdir()
    os.environ.update(
        YOLO_CONFIG_DIR=str(settings_path),
        YOLO_AUTOINSTALL="false",
        YOLO_OFFLINE="true",
    )
    enforce_offline()
    if args.torch_runtime is not None:
        sys.path.insert(0, str(args.torch_runtime.resolve()))
    import torch
    from ultralytics import YOLO, settings

    settings.update({"sync": False})
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    gpu = None
    if args.device == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("Requested CUDA unavailable; no implicit fallback")
        free, total = torch.cuda.mem_get_info()
        if free < 2 * 1024**3:
            raise RuntimeError("Less than 2 GiB GPU memory available")
        torch.cuda.set_per_process_memory_fraction(min(0.85, free * 0.85 / total))
        gpu = {
            "name": torch.cuda.get_device_name(),
            "total_bytes": total,
            "free_before": free,
            "cuda_build": torch.version.cuda,
            "cudnn": torch.backends.cudnn.version(),
        }
        torch.cuda.reset_peak_memory_stats()
    started = perf_counter_ns()
    deadline = started + args.max_run_minutes * 60 * 1_000_000_000
    (args.output / "run-config.json").write_text(
        json.dumps(
            {
                "model": args.model,
                "model_sha256": model_record["sha256"],
                "source_sha256": population["source_sha256"],
                "population_sha256": digest(population_path),
                "scope": "RESIDUAL_ONLY" if args.residual else "FIXED_60_188",
                "device": args.device,
                "warmup": args.warmup,
                "max_run_minutes": args.max_run_minutes,
                "budget_check": "BETWEEN_CALLS_NOT_PREEMPTIVE",
                "runner_sha256": digest(Path(__file__).resolve()),
            },
            indent=2,
        )
        + "\n"
    )
    model = YOLO(str(weights))
    startup = perf_counter_ns() - started
    process = psutil.Process()
    durations = []
    rss = []
    vendor_timings = {key: [] for key in ("preprocess", "inference", "postprocess")}
    entity_counts = []
    warmup_ns = 0
    with (
        args.video.open("rb") as source,
        av.open(
            source,
            options={
                "format_whitelist": "mov,matroska,webm,avi",
                "protocol_whitelist": "file",
            },
        ) as container,
        (args.output / "predictions.jsonl").open("x", encoding="utf-8") as sink,
    ):
        stream = container.streams.video[0]
        stream.codec_context.thread_count = 1
        for index, timestamp in enumerate(targets):
            check_budget(perf_counter_ns(), deadline, psutil.virtual_memory().available)
            image = exact_frame(container, stream, timestamp)
            kwargs = dict(
                imgsz=640,
                device=args.device,
                conf=0.05,
                max_det=100,
                verbose=False,
                save=False,
                stream=False,
            )
            if index == 0:
                warmup_started = perf_counter_ns()
                for _ in range(args.warmup):
                    check_budget(perf_counter_ns(), deadline, psutil.virtual_memory().available)
                    model.predict(image, **kwargs)
                if args.device == "cuda":
                    torch.cuda.synchronize()
                warmup_ns = perf_counter_ns() - warmup_started
                if (
                    model.predictor.device.type != args.device
                    or next(model.predictor.model.backend.model.parameters()).device.type
                    != args.device
                    or model.predictor.model.fp16
                ):
                    raise RuntimeError("Actual model execution device differs from request")
            if args.device == "cuda":
                torch.cuda.synchronize()
            started = perf_counter_ns()
            output = model.predict(image, **kwargs)[0]
            if output.boxes.data.device.type != args.device:
                raise RuntimeError("Inference output device differs from request")
            if args.device == "cuda":
                torch.cuda.synchronize()
            elapsed = perf_counter_ns() - started
            check_budget(perf_counter_ns(), deadline, psutil.virtual_memory().available)
            durations.append(elapsed)
            rss.append(process.memory_info().rss)
            for key in vendor_timings:
                vendor_timings[key].append(int(output.speed[key] * 1_000_000))
            entity_counts.append(len(output.boxes))
            regions = [
                {
                    "box": list(map(float, box)),
                    "concept": output.names.get(int(category)),
                    "confidence": float(confidence),
                    "confidence_basis": "JOINT_DETECTION_SCORE",
                    "status": "MODEL_PREDICTION_NOT_GROUND_TRUTH",
                }
                for box, confidence, category in zip(
                    output.boxes.xyxy.tolist(),
                    output.boxes.conf.tolist(),
                    output.boxes.cls.tolist(),
                    strict=True,
                )
            ]
            sink.write(
                json.dumps(
                    {
                        "source_ns": timestamp,
                        "regions": regions,
                        "call_ns": elapsed,
                        "vendor_stages_ms": output.speed,
                        "rss_bytes": rss[-1],
                    },
                    allow_nan=False,
                )
                + "\n"
            )
            sink.flush()
            if (index + 1) % 30 == 0:
                print(f"{args.model}: {index + 1}/{len(targets)}", flush=True)
    from v0_analyze import quantiles

    report = {
        "status": "COMPLETE_MODEL_SCREENING_NOT_PIPELINE_QUALIFICATION",
        "model": args.model,
        "model_sha256": model_record["sha256"],
        "source_sha256": population["source_sha256"],
        "population_sha256": digest(population_path),
        "predictions_sha256": digest(args.output / "predictions.jsonl"),
        "frames": len(targets),
        "scope": "RESIDUAL_ONLY" if args.residual else "FIXED_60_188",
        "alert_denominator": len(population["targets"]) if args.residual else 60,
        "event_denominator": None if args.residual else 188,
        "provider": "torch " + args.device,
        "precision": "FP32",
        "input_size": 640,
        "warmup_calls": args.warmup,
        "max_run_minutes": args.max_run_minutes,
        "budget_check": "BETWEEN_CALLS_NOT_PREEMPTIVE",
        "threads": 2,
        "startup_ns": startup,
        "startup_scope": "MODEL_CONSTRUCTOR_ONLY",
        "warmup_ns": warmup_ns,
        "constructor_plus_warmup_ns": startup + warmup_ns,
        "vendor_stages": {key: quantiles(samples) for key, samples in vendor_timings.items()},
        "entity_observations": sum(entity_counts),
        "maximum_entities_per_frame": max(entity_counts),
        "call_time": quantiles(durations),
        "max_sampled_rss_bytes": max(rss),
        "sampled_rss_not_peak": True,
        "torch": torch.__version__,
        "vram_bytes": torch.cuda.max_memory_reserved() if args.device == "cuda" else None,
        "gpu": gpu,
        "adopted": False,
        "semantic_accuracy_measured": False,
    }
    temporary = args.output / "summary.tmp"
    temporary.write_text(json.dumps(report, indent=2) + "\n")
    temporary.replace(args.output / "summary.json")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
