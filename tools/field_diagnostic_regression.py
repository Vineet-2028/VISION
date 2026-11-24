"""Isolated same-source engine regression; no physical camera/delivery claims."""

import argparse
import json
from pathlib import Path
from time import perf_counter_ns

import psutil


def run(output: Path, mode: str, seconds: int, diagnostics: bool, recording: bool) -> None:
    from alpha_field_gateway import hash_file, release_profile
    from rescue_runtime import activate_onnx

    if psutil.virtual_memory().available < 3 * 1024**3:
        raise RuntimeError("BLOCKED_BY_AVAILABLE_RAM: 3 GiB startup reserve")
    root = Path(__file__).resolve().parents[1]
    runtime = root / "benchmark-results/v0-rescue"
    output.mkdir(parents=True, exist_ok=False)
    manifest = root / "benchmark-results/v02/VISION_CONTROLLED_ALPHA_V1/manifest.json"
    release_hash = hash_file(manifest)
    if release_hash != "ecd83215cc8f8e144ec9126b61415e8ca38b854a4126cfdbc6e52d55affa6254":
        raise ValueError("Frozen release manifest mismatch")
    profile = release_profile(manifest)
    if mode == "OFFLINE_REPLAY":
        # Canonical offline coverage must process every frame, without realtime rescue.
        profile["realtime_rescue"] = False
    config = output / "input.json"
    config.write_text(json.dumps(profile), encoding="utf-8")
    _, handles = activate_onnx(
        runtime / "gpu-runtime", runtime / "gpu-libraries", runtime / "cudnn-9.10/nvidia/cudnn/bin"
    )
    stats = {
        "release_sha256": release_hash,
        "runner_sha256": hash_file(Path(__file__)),
        "field_worker_sha256": hash_file(root / "tools/alpha_field_worker.py"),
        "updates": 0,
        "serialized_bytes": 0,
        "serialization_ns": 0,
        "generation_ns": 0,
        "generated_updates": 0,
        "truncated_updates": 0,
        "writer_queue_peak": 0,
        "scope": "RECORDED_ENGINE_SOURCE_NOT_PHONE_GATEWAY_OR_ACOUSTIC_TEST",
        "diagnostics": diagnostics,
        "recording": recording,
    }
    try:
        import v0_replay

        from perception_lab import pipeline
        from perception_lab.field_detector_diagnostics import DiagnosticPicoDet
        from perception_lab.field_tracking_diagnostics import DiagnosticTracker

        original_pipeline = v0_replay.TracePipeline
        original_recorder = v0_replay.TraceRecorder
        if diagnostics:
            v0_replay.PicoDetDetector = DiagnosticPicoDet
            pipeline.AssociationTracker = DiagnosticTracker

        class GuardedPipeline(original_pipeline):
            def process(self, item):
                if psutil.virtual_memory().available < 2 * 1024**3:
                    raise RuntimeError("BLOCKED_BY_AVAILABLE_RAM: 2 GiB runtime reserve")
                super().process(item)

        with (output / "diagnostics.jsonl").open("x", encoding="utf-8") as stream:

            class DiagnosticRecorder(original_recorder):
                def write_result(self, result):
                    super().write_result(result)
                    stats["updates"] += 1
                    if not diagnostics:
                        return
                    from alpha_field_worker import bounded_object_evidence

                    start = perf_counter_ns()
                    payload = {
                        "objects": bounded_object_evidence(
                            result, self.owner.tracker.diagnostic, []
                        ),
                        "detector": self.owner.detector.diagnostic,
                    }
                    stats["generation_ns"] += perf_counter_ns() - start
                    stats["generated_updates"] += 1
                    if not recording:
                        return
                    if stats["serialized_bytes"] >= 4 * 1024**2:
                        stats["truncated_updates"] += 1
                        return
                    start = perf_counter_ns()
                    encoded = json.dumps(payload) + "\n"
                    encoded_size = len(encoded.encode())
                    if (
                        encoded_size <= 32768
                        and stats["serialized_bytes"] + encoded_size <= 4 * 1024**2
                    ):
                        stream.write(encoded)
                        stats["serialized_bytes"] += encoded_size
                    else:
                        stats["truncated_updates"] += 1
                    stats["serialization_ns"] += perf_counter_ns() - start

            v0_replay.TracePipeline = GuardedPipeline
            v0_replay.TraceRecorder = DiagnosticRecorder
            v0_replay.run(
                config, output / "replay", mode, seconds, trace_mode="COMPACT_ALPHA_TRACE"
            )
        stats["status"] = "COMPLETE"
    except BaseException:
        stats["status"] = "INCOMPLETE"
        raise
    finally:
        (output / "diagnostic-summary.json").write_text(
            json.dumps(stats, indent=2), encoding="utf-8"
        )
        for handle in handles:
            handle.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=["REALTIME", "OFFLINE_REPLAY"], required=True)
    parser.add_argument("--seconds", type=int, default=600)
    parser.add_argument("--diagnostics", action="store_true")
    parser.add_argument("--recording", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.seconds <= 1500:
        parser.error("Duration must be between 1 and 1500 seconds")
    if args.recording and not args.diagnostics:
        parser.error("Recording requires diagnostic candidate")
    run(args.output, args.mode, args.seconds, args.diagnostics, args.recording)
