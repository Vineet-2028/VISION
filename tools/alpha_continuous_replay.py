"""Marker-independent continuous CPU replay; presentation-only paired ablation.

This fixed source-time admission is NOT historical realtime admission or a speed
qualification. No population markers participate in decoding or scheduling.
"""

import argparse
import atexit
import hashlib
import json
from pathlib import Path
from time import perf_counter_ns

import av
from v0_replay import TracePipeline, TraceRecorder, digest

from perception_lab.config import Calibration, LabConfig
from perception_lab.contracts import Frame, FrameIdentity, PixelFormat, TimingProvenance
from perception_lab.edge_runtime import PicoDetDetector
from perception_lab.geometry import CoreGeometry
from perception_lab.preprocessing import BasicPreprocessor
from perception_lab.sources import pts_to_ns


class Admission:
    """Select first authoritative frame at/after each fixed source-time deadline."""

    def __init__(self, interval_ns, end_ns):
        if interval_ns <= 0 or end_ns <= 0:
            raise ValueError("Positive cadence and duration required")
        self.interval_ns, self.end_ns = interval_ns, end_ns
        self.next_ns, self.last_ns = 0, -1

    def accept(self, stamp):
        if stamp <= self.last_ns:
            raise ValueError("Non-monotonic source PTS")
        self.last_ns = stamp
        if stamp >= self.end_ns or stamp < self.next_ns:
            return False
        self.next_ns = (stamp // self.interval_ns + 1) * self.interval_ns
        return True


class ContinuousSource:
    def __init__(self, video, source_id, interval_ns, end_ns, deadline):
        self.video, self.source_id = video, source_id
        self.admission = Admission(interval_ns, end_ns)
        self.deadline = deadline
        self.frames = 0
        self.finished = False
        self.failure_code = None
        self.free_ram_at_stop = None
        self.admission_hash = hashlib.sha256()

    def __iter__(self):
        import psutil

        with (
            self.video.open("rb") as source,
            av.open(
                source, options={"format_whitelist": "mov", "protocol_whitelist": "file"}
            ) as container,
        ):
            stream = container.streams.video[0]
            stream.codec_context.thread_count = 1
            for sequence, native in enumerate(container.decode(stream)):
                stamp = pts_to_ns(native.pts, native.time_base)
                if stamp is None or native.is_corrupt:
                    self.failure_code = "INVALID_SOURCE_FRAME"
                    raise ValueError("Invalid source frame; no substitution")
                if stamp >= self.admission.end_ns:
                    self.finished = True
                    break
                if not self.admission.accept(stamp):
                    continue
                if perf_counter_ns() >= self.deadline:
                    self.failure_code = "WALL_BUDGET_EXHAUSTED"
                    raise RuntimeError("Wall budget exhausted; incomplete")
                available = psutil.virtual_memory().available
                if available < 2 * 1024**3:
                    self.failure_code = "FREE_RAM_RESERVE_REACHED"
                    self.free_ram_at_stop = available
                    raise RuntimeError("2 GiB free RAM reserve reached; incomplete")
                now = perf_counter_ns()
                pixels = native.to_ndarray(format="rgb24")
                self.frames += 1
                self.admission_hash.update(f"{sequence}:{stamp}\n".encode())
                yield Frame(
                    FrameIdentity(
                        self.source_id, sequence, stamp, TimingProvenance.AUTHORITATIVE_PTS
                    ),
                    pixels,
                    PixelFormat.RGB,
                    now,
                    perf_counter_ns(),
                )
        if not self.finished:
            self.failure_code = "PREMATURE_SOURCE_END"
            raise ValueError("Source ended before requested window; incomplete")

    def close(self):
        pass  # Decoder and file are owned by generator context managers.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--arm", choices=("A", "B"), required=True)
    parser.add_argument("--seconds", type=int, default=600)
    parser.add_argument("--device", choices=("cpu", "cuda:0"), default="cpu")
    parser.add_argument("--ort-runtime", type=Path)
    parser.add_argument("--cuda-libraries", type=Path)
    parser.add_argument("--cudnn-directory", type=Path)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 1500:
        parser.error("seconds must be between 1 and 1500")
    runtime_paths = (args.ort_runtime, args.cuda_libraries, args.cudnn_directory)
    if args.device == "cuda:0":
        if not all(runtime_paths):
            parser.error("CUDA requires the three explicit isolated runtime directories")
        from rescue_runtime import activate_onnx

        _, directories = activate_onnx(*runtime_paths)
        for directory in directories:
            atexit.register(directory.close)
    elif any(runtime_paths):
        parser.error("CPU replay cannot accept CUDA runtime overrides")
    root = Path(__file__).resolve().parents[1]
    raw = json.loads(
        (
            root / "benchmark-results/v0-rescue/realtime-06-gpu-no-depth/configuration.json"
        ).read_text()
    )
    video = Path(raw["input"])
    source_hash = digest(video)
    if source_hash != "e011aa64a65aa9aeb00fce657312362742d12dfd9170f76878e2a784ab1fc5e2":
        raise ValueError("Frozen source mismatch")
    ontology = root / "configs/perception/ontology/vision-domain-v2.json"
    raw.update(
        mode="OFFLINE_REPLAY",
        realtime_rescue=False,
        drop_policy="PROCESS_ALL",
        max_staleness_ns=None,
        start_ns=0,
        end_ns=args.seconds * 1_000_000_000,
        record_session=False,
        visualization=False,
        output=str(args.output.resolve()),
        entity_semantics_ontology=str(ontology),
        semantic_presentation_enabled=args.arm == "B",
        depth=None,
        motion=None,
        segmentation=None,
    )
    raw["detector"].update(device=args.device, threads=2)
    config = LabConfig.model_validate(raw)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "configuration.json").write_text(json.dumps(config.model_dump(), indent=2))
    runtime_files = sorted((root / "apps/perception-lab/src/perception_lab").glob("*.py"))
    runtime_files += [
        Path(__file__),
        root / "tools/v0_replay.py",
        root / "tools/alpha_trace.py",
        root / "tools/rescue_trace.py",
        root / "tools/rescue_runtime.py",
        root / "packages/guardian-core/target/guardian-core-0.1.0.jar",
    ]
    (args.output / "source-manifest.json").write_text(
        json.dumps({str(p.relative_to(root)): digest(p) for p in runtime_files}, indent=2)
    )
    calibration = Calibration.model_validate_json(Path(config.calibration).read_text())
    geometry = CoreGeometry(calibration)
    detector = PicoDetDetector(
        Path(config.detector.weights),
        config.detector.sha256,
        confidence=config.detector.confidence,
        device=args.device,
        threads=2,
    )
    detector.enable_entity_semantics(ontology)
    source = ContinuousSource(
        video,
        config.source_id,
        200_000_000,
        args.seconds * 1_000_000_000,
        perf_counter_ns() + 45 * 60 * 1_000_000_000,
    )
    recorder = TraceRecorder(config, calibration, args.output)
    with (args.output / "updates.jsonl").open("x") as trace:
        pipeline = TracePipeline(
            config,
            BasicPreprocessor(geometry, config.preprocess),
            recorder,
            detector=detector,
            motion_geometry=geometry,
            trace=trace,
        )
        try:
            summary = pipeline.run(source)
        except BaseException:
            # Pipeline intentionally sanitizes exception text. Preserve bounded machine
            # reasons here so resource stops cannot be mistaken for completed runs.
            status = {
                "status": "INCOMPLETE",
                "source_failure_code": source.failure_code or "NOT_CLASSIFIED",
                "pipeline_failure_code": recorder.manifest.get("failure"),
                "admitted": source.frames,
                "free_ram_at_stop": source.free_ram_at_stop,
            }
            temporary = args.output / "failure.tmp"
            temporary.write_text(json.dumps(status, indent=2))
            temporary.replace(args.output / "failure.json")
            raise
    if (
        not source.finished
        or summary.get("failure") is not None
        or summary["summary"]["frame_counts"].get("failed", 0)
    ):
        raise RuntimeError("Incomplete or failed replay cannot qualify")
    size = (args.output / "updates.jsonl").stat().st_size
    report = {
        "status": "COMPLETE_CONTINUOUS_OFFLINE_PRESENTATION_ABLATION",
        "arm": args.arm,
        "seconds": args.seconds,
        "admitted": source.frames,
        "source_sha256": source_hash,
        "admission_sha256": source.admission_hash.hexdigest(),
        "updates_sha256": digest(args.output / "updates.jsonl"),
        "ontology_sha256": digest(ontology),
        "runtime": detector.runtime_metadata,
        "trace_bytes": size,
        "trace_bytes_per_admitted_update": size / source.frames,
        "writer_mode": "SYNCHRONOUS",
        "writer_queue_peak": 0,
        "writer_drops": 0,
        "instrumentation_wall_recent_window": pipeline.instrumentation.summary(),
        "instrumentation_cpu_time": "NOT_MEASURED",
        "rss_peak": pipeline.rss_peak,
        "summary": summary,
        "limitations": [
            "Fixed 200 ms source-time admission, not historical realtime",
            "A retains semantics and disables only presentation attachment",
            "Motion, depth, segmentation unavailable in both arms",
            "No historical lineage reconstruction or marker-driven processing",
        ],
    }
    temporary = args.output / "summary.tmp"
    temporary.write_text(json.dumps(report, indent=2))
    temporary.replace(args.output / "continuous-summary.json")
    print(json.dumps({"arm": args.arm, "admitted": source.frames, "trace_bytes": size}), flush=True)


if __name__ == "__main__":
    main()
