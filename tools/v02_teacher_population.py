"""Pinned local open-set teacher on all fixed frames; MODEL_PSEUDO_LABEL only."""

import argparse
import json
import os
import platform
import sys
from pathlib import Path
from time import perf_counter_ns

import av
from acquire_offline_teacher import verify
from v0_analyze import quantiles
from v02_candidate_population import (
    check_budget,
    digest,
    exact_frame,
    residual_targets,
    source_targets,
)

from perception_lab.offline import enforce_offline


def read_prefix(path, targets):
    if path.stat().st_size > 256 * 1024**2:
        raise ValueError("Teacher checkpoint exceeds size bound")
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    if len(rows) > len(targets) or [r["source_ns"] for r in rows] != targets[: len(rows)]:
        raise ValueError("Teacher checkpoint is not the exact ordered population prefix")
    if any(r["status"] != "MODEL_PSEUDO_LABEL" or r["call_ns"] < 0 for r in rows):
        raise ValueError("Invalid teacher checkpoint provenance/timing")
    return rows


def main():
    import psutil

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--torch-runtime", type=Path)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--resume-from", type=Path)
    parser.add_argument("--max-run-minutes", type=float, default=15)
    parser.add_argument("--residual", type=Path)
    parser.add_argument("--warmup", type=int, default=0)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    population_path = args.residual or root / "benchmark-results/v02/populations-02.json"
    population = json.loads(population_path.read_text())
    targets = residual_targets(population) if args.residual else source_targets(population)
    if not 0 <= args.warmup <= 3 or (args.residual and args.resume_from):
        raise ValueError(
            "Bounded warmup required; residual screening cannot resume old populations"
        )
    if not 0 < args.max_run_minutes <= 60:
        raise ValueError("GPU segment time bound must be between 0 and 60 minutes")
    prior = read_prefix(args.resume_from, targets) if args.resume_from else []
    query_path = root / "configs/perception/teacher-queries-v1.json"
    queries = json.loads(query_path.read_text())
    registry = json.loads((root / "configs/perception/offline-teacher-v1.json").read_text())
    weights = root / "benchmark-results/v02/models/grounding-dino-base"
    for record in registry["files"]:
        verify(weights / record["name"], record)
    video = root / "datasets/sentinel_first_person_v1/raw/Screen Recording 2026-10-16 223504.mp4"
    if digest(video) != population["source_sha256"]:
        raise ValueError("Source mismatch")
    if not 1 <= len(queries["queries"]) <= 32 or not 1 <= queries["chunk_size"] <= 16:
        raise ValueError("Unbounded teacher vocabulary")
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "run-config.json").write_text(
        json.dumps(
            {
                "runner_sha256": digest(Path(__file__).resolve()),
                "source_sha256": population["source_sha256"],
                "population_sha256": digest(population_path),
                "query_sha256": digest(query_path),
                "revision": registry["revision"],
                "device": args.device,
                "warmup": args.warmup,
                "max_run_minutes": args.max_run_minutes,
            },
            indent=2,
        )
    )
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    enforce_offline()
    if args.torch_runtime is not None:
        sys.path.insert(0, str(args.torch_runtime.resolve()))
    import torch
    from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    hardware = {
        "cpu": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "ram_bytes": psutil.virtual_memory().total,
        "torch": torch.__version__,
        "cuda_build": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(),
    }
    if args.device == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("Requested CUDA is unavailable; no implicit CPU fallback")
        free, total = torch.cuda.mem_get_info()
        if free < 2 * 1024**3:
            raise RuntimeError("Insufficient GPU headroom for teacher")
        torch.cuda.set_per_process_memory_fraction(min(0.85, free * 0.85 / total))
        hardware.update(
            gpu=torch.cuda.get_device_name(), vram_total_bytes=total, vram_free_before=free
        )
        torch.cuda.reset_peak_memory_stats()
    startup_started = perf_counter_ns()
    processor = AutoProcessor.from_pretrained(
        weights, local_files_only=True, trust_remote_code=False
    )
    model = (
        AutoModelForZeroShotObjectDetection.from_pretrained(
            weights, local_files_only=True, trust_remote_code=False, use_safetensors=True
        )
        .eval()
        .to(args.device)
    )
    if next(model.parameters()).device.type != args.device:
        raise RuntimeError("Teacher actual device mismatch")
    startup_ns = perf_counter_ns() - startup_started
    prompts = [
        ". ".join(queries["queries"][i : i + queries["chunk_size"]]) + "."
        for i in range(0, len(queries["queries"]), queries["chunk_size"])
    ]
    process = psutil.Process()
    durations = [r["call_ns"] for r in prior]
    rss = [r["rss_bytes"] for r in prior]
    stage_samples = {key: [] for key in ("preprocess_upload", "inference", "postprocess_download")}
    entity_counts = []
    warmup_ns = 0
    segment_started = perf_counter_ns()
    with (
        video.open("rb") as source,
        av.open(
            source, options={"format_whitelist": "mov", "protocol_whitelist": "file"}
        ) as container,
        (args.output / "predictions.jsonl").open("x") as sink,
    ):
        stream = container.streams.video[0]
        stream.codec_context.thread_count = 1
        for row in prior:
            sink.write(json.dumps(row) + "\n")
        sink.flush()
        if args.warmup:
            warmup_started = perf_counter_ns()
            warm_image = exact_frame(container, stream, targets[0])[:, :, ::-1].copy()
            for _ in range(args.warmup):
                for prompt in prompts:
                    check_budget(
                        perf_counter_ns(),
                        segment_started + args.max_run_minutes * 60e9,
                        psutil.virtual_memory().available,
                    )
                    warm_inputs = processor(images=warm_image, text=prompt, return_tensors="pt").to(
                        args.device
                    )
                    if warm_inputs.input_ids.shape[1] > 256:
                        raise ValueError("Teacher query token bound exceeded")
                    with torch.inference_mode():
                        model(**warm_inputs)
            if args.device == "cuda":
                torch.cuda.synchronize()
            del warm_inputs, warm_image
            warmup_ns = perf_counter_ns() - warmup_started
        for index, timestamp in enumerate(targets):
            if index < len(prior):
                continue
            if perf_counter_ns() - segment_started > args.max_run_minutes * 60e9:
                raise RuntimeError("Teacher time budget reached; checkpoint retained for resume")
            if psutil.virtual_memory().available < 2 * 1024**3:
                raise RuntimeError("Teacher stopped: less than 2 GiB RAM headroom")
            image = exact_frame(container, stream, timestamp)[:, :, ::-1].copy()
            regions = []
            stages = dict.fromkeys(stage_samples, 0)
            started = perf_counter_ns()
            for prompt in prompts:
                tick = perf_counter_ns()
                inputs = processor(images=image, text=prompt, return_tensors="pt").to(args.device)
                if inputs.input_ids.shape[1] > 256:
                    raise ValueError("Teacher query token bound exceeded")
                if args.device == "cuda":
                    torch.cuda.synchronize()
                stages["preprocess_upload"] += perf_counter_ns() - tick
                tick = perf_counter_ns()
                with torch.inference_mode():
                    output = model(**inputs)
                if args.device == "cuda":
                    torch.cuda.synchronize()
                stages["inference"] += perf_counter_ns() - tick
                tick = perf_counter_ns()
                if (
                    output.logits.device.type != args.device
                    or output.pred_boxes.device.type != args.device
                ):
                    raise RuntimeError("Teacher output device differs from requested device")
                result = processor.post_process_grounded_object_detection(
                    output,
                    inputs.input_ids,
                    threshold=queries["box_threshold"],
                    text_threshold=queries["text_threshold"],
                    target_sizes=[image.shape[:2]],
                )[0]
                for box, confidence, label in zip(
                    result["boxes"].tolist(),
                    result["scores"].tolist(),
                    result["text_labels"],
                    strict=True,
                ):
                    regions.append(
                        {
                            "box": box,
                            "concept": label or None,
                            "confidence": confidence,
                            "confidence_basis": "TEXT_GROUNDING_SCORE",
                            "status": "MODEL_PSEUDO_LABEL",
                        }
                    )
                stages["postprocess_download"] += perf_counter_ns() - tick
            elapsed = perf_counter_ns() - started
            for key in stage_samples:
                stage_samples[key].append(stages[key])
            entity_counts.append(len(regions))
            durations.append(elapsed)
            rss.append(process.memory_info().rss)
            sink.write(
                json.dumps(
                    {
                        "source_ns": timestamp,
                        "regions": regions,
                        "call_ns": elapsed,
                        "stages_ns": stages,
                        "rss_bytes": rss[-1],
                        "status": "MODEL_PSEUDO_LABEL",
                    }
                )
                + "\n"
            )
            sink.flush()
            print(f"Teacher: {index + 1}/{len(targets)}; {elapsed / 1e9:.2f}s", flush=True)
    report = {
        "status": "COMPLETE_OFFLINE_TEACHER_PSEUDO_LABELS",
        "model": registry["repository"],
        "revision": registry["revision"],
        "source_sha256": population["source_sha256"],
        "population_sha256": digest(population_path),
        "query_sha256": digest(query_path),
        "predictions_sha256": digest(args.output / "predictions.jsonl"),
        "frames": len(targets),
        "scope": "RESIDUAL_ONLY" if args.residual else "FIXED_60_188",
        "warmup_calls_per_prompt": args.warmup,
        "startup_ns": startup_ns,
        "warmup_ns": warmup_ns,
        "stage_timings": {key: quantiles(values) for key, values in stage_samples.items()},
        "stage_measurement_scope": "CURRENT_PROCESS_SEGMENT; ALL_PROMPTS_PER_FRAME",
        "entity_observations_current_segment": sum(entity_counts),
        "maximum_regions_per_frame_current_segment": max(entity_counts, default=0),
        "call_time": quantiles(durations),
        "max_sampled_rss_bytes": max(rss),
        "provider": "torch " + args.device,
        "precision": "FP32",
        "threads": 2,
        "vram_bytes": torch.cuda.max_memory_reserved() if args.device == "cuda" else None,
        "hardware": hardware,
        "adopted": False,
        "resumed_prefix_frames": len(prior),
        "resumed_prefix_sha256": digest(args.resume_from) if args.resume_from else None,
        "resumed_input_binding": "CURRENT_SESSION_COMMAND_PROVENANCE_NOT_EMBEDDED_IN_OLD_ROWS"
        if prior
        else None,
        "vram_measurement_scope": "CURRENT_PROCESS_SEGMENT_ONLY",
        "limitations": [
            "Prompt-conditioned, not unrestricted object discovery",
            "Adaptive queries from same footage; not held-out accuracy",
            "Warmup excluded" if args.warmup else "No warmup; first call included",
            "Cross-prompt duplicate regions retained for audit",
        ],
    }
    temporary = args.output / "summary.tmp"
    temporary.write_text(json.dumps(report, indent=2))
    temporary.replace(args.output / "summary.json")


if __name__ == "__main__":
    main()
