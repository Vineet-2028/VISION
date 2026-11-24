"""Measurement-only V0 replay. Does not change scheduling or freshness policy.

Private JSONL retains per-update measurements; aggregate quantiles are bounded
recent-window statistics, never silently presented as whole-run percentiles.
"""

import argparse
import hashlib
import json
import platform
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from time import perf_counter_ns

from alpha_trace import compact_alpha
from rescue_trace import AsyncTrace

from perception_lab.config import Calibration, LabConfig, read_json
from perception_lab.depth_runtime import DepthAnythingProvider
from perception_lab.depth_synthetic import SyntheticDepthProvider
from perception_lab.edge_runtime import PicoDetDetector, YoloXDetector
from perception_lab.geometry import CoreGeometry
from perception_lab.metrics import Distribution
from perception_lab.orientation_preprocessing import build_preprocessor
from perception_lab.pipeline import Pipeline
from perception_lab.recording import SessionRecorder
from perception_lab.semantic_runtime import OnnxSemanticSegmenter, SyntheticSegmenter
from perception_lab.sources import VideoFileSource


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def compact(value):
    """Strip large histories and repeated provenance, not stage decisions or IDs."""
    if is_dataclass(value):
        if type(value).__name__ == "TrackSemanticState":
            return {
                **{
                    f.name: compact(getattr(value, f.name))
                    for f in fields(value)
                    if f.name != "evidence"
                },
                "evidence_count": len(value.evidence),
            }
        return {
            f.name: (
                asdict(getattr(value, f.name))
                if f.name == "semantic_evidence" and is_dataclass(getattr(value, f.name))
                else compact(getattr(value, f.name))
            )
            for f in fields(value)
            if f.name
            not in {
                "history",
                "provenance",
                "position_sources",
                "samples",
                "regions",
                "projected_ground",
                "hypotheses",
            }
        }
    if isinstance(value, (tuple, list)):
        return [compact(v) for v in value]
    if isinstance(value, dict):
        return {k: compact(v) for k, v in value.items()}
    return value


class TraceDistribution(Distribution):
    def __init__(self, name, owner, capacity):
        super().__init__(capacity)
        self.name, self.owner = name, owner

    def add(self, value):
        super().add(value)
        if self.owner.active and self.name not in {"decode", "conversion"}:
            end = perf_counter_ns()
            self.owner.spans.append({"stage": self.name, "end_ns": end, "duration_ns": value})


class TraceRecorder(SessionRecorder):
    def write_result(self, result):
        super().write_result(result)
        self.owner.result = result


class TracePipeline(Pipeline):
    def __init__(self, *args, trace, trace_mode="FULL", **kwargs):
        import psutil

        super().__init__(*args, **kwargs)
        if trace_mode not in {"FULL", "COMPACT_ALPHA_TRACE"}:
            raise ValueError("Unknown trace detail mode")
        self.trace_mode = trace_mode
        self.trace = trace
        self.active = False
        self.spans = []
        self.result = None
        self.previous_publication = None
        self.intervals = Distribution(2048)
        self.instrumentation = Distribution(2048)
        self.trace_bytes = 0
        self.trace_rows = 0
        self.serialization_ns = 0
        self.write_ns = 0
        self.process_info = psutil.Process()
        self.rss_start = self.rss_peak = self.process_info.memory_info().rss
        self.rss_samples = []
        self.recorder.owner = self
        self.metrics.stages = {k: TraceDistribution(k, self, 2048) for k in self.metrics.stages}

    def process(self, item):
        compact = (
            compact_alpha if self.trace_mode == "COMPACT_ALPHA_TRACE" else globals()["compact"]
        )
        self.active, self.spans, self.result = True, [], None
        try:
            super().process(item)
        finally:
            self.active = False
        if self.result is None:
            return
        published = perf_counter_ns()
        if self.previous_publication is not None:
            self.intervals.add(published - self.previous_publication)
        self.previous_publication = published
        result = self.result
        observation = result.identity.observation_ns
        realtime = self.config.mode == "REALTIME"
        # Offline due is admission time, NOT a replay-clock anchor.
        age = published - item.due_ns if realtime else None
        attention_end = next((s["end_ns"] for s in self.spans if s["stage"] == "attention"), None)
        candidates = []
        if result.attention_decision_set is not None:
            batch = result.attention_decision_set
            decisions = [(d, "SELECTED") for d in batch.selected]
            decisions += [(s.decision, s.reason) for s in batch.suppressed]
            for decision, disposition in decisions:
                source = decision.source_observation_ns
                candidates.append(
                    {
                        "entity_id": compact(decision.entity_id),
                        "disposition": disposition,
                        "decision": decision.decision,
                        "source_observation_ns": source,
                        "source_age_at_attention_ns": (
                            observation - source + max(0, attention_end - item.due_ns)
                            if realtime and source is not None and attention_end is not None
                            else None
                        ),
                        "source_age_media_ns": observation - source if source is not None else None,
                    }
                )
        rss = self.process_info.memory_info().rss
        self.rss_peak = max(self.rss_peak, rss)
        if len(self.rss_samples) < 121 and observation >= len(self.rss_samples) * 5_000_000_000:
            self.rss_samples.append({"source_ns": observation, "rss": rss})
        row = {
            "schema_version": 3 if self.trace_mode == "COMPACT_ALPHA_TRACE" else 2,
            "trace_mode": self.trace_mode,
            "mode": self.config.mode,
            "identity": compact(result.identity),
            "width": result.width,
            "height": result.height,
            "due_monotonic_ns": item.due_ns if realtime else None,
            "accepted_monotonic_ns": item.accepted_ns,
            "publication_monotonic_ns": published,
            "source_to_publication_age_ns": age,
            "timing": compact(result.timing),
            "components": [
                {**compact(component), "component_type": component.provenance.component_type}
                for component in result.components
            ],
            "spans": self.spans,
            "rss": rss,
            "attention_candidates": candidates,
            "user_motion_heading": compact(result.user_motion_heading),
            "camera_view_quality": compact(result.camera_view_quality),
            "camera_orientation": compact(result.camera_orientation),
            "scene_capability": result.scene_capability,
            "world": None
            if result.world_state is None
            else {
                "state_timestamp": result.world_state.state_timestamp,
                "source_ages": compact(result.world_state.source_ages),
                "scene_quality": compact(result.world_state.scene_quality),
                "entities": [
                    {
                        "entity_id": compact(e.entity_id),
                        "source_track_id": compact(e.source_track_id),
                        "category": e.category,
                        "box": compact(e.image_geometry),
                        "observation_age_ns": e.observation_age_ns,
                        "observation_status": e.observation_status,
                        "entity_observation": compact(e.entity_observation),
                        "track_semantics": compact(e.track_semantics),
                    }
                    for e in result.world_state.entities
                ],
            },
        }
        for name in (
            "detector",
            "tracks",
            "corridor_analysis",
            "trajectory_set",
            "interaction_analysis",
            "risk_assessment_set",
            "attention_decision_set",
            "alert_output_set",
        ):
            row[name] = compact(getattr(result, name))
        if self.config.realtime_rescue:
            row["provider_state"] = {
                "detector": {
                    "runtime": self.detector.provenance.runtime,
                    "available": result.detector is not None,
                },
                "depth": {
                    "runtime": self.depth.provenance.runtime,
                    "source": compact(result.depth.identity) if result.depth else None,
                },
                "segmentation": {
                    "runtime": self.segmentation.provenance.runtime,
                    "source": compact(result.segmentation.identity)
                    if result.segmentation
                    else None,
                },
                "flow": {
                    "runtime": self.flow.provenance.runtime,
                    "source": compact(result.optical_flow.identity)
                    if result.optical_flow
                    else None,
                },
            }
            row["errors"] = compact(result.errors)
            row["warnings"] = compact(result.warnings)
        if isinstance(self.trace, AsyncTrace):
            self.trace.submit(row)
        else:
            started = perf_counter_ns()
            payload = json.dumps(row, allow_nan=False, separators=(",", ":")) + "\n"
            self.serialization_ns += perf_counter_ns() - started
            size = len(payload.encode("utf-8"))
            started = perf_counter_ns()
            self.trace.write(payload)
            self.write_ns += perf_counter_ns() - started
            self.trace_bytes += size
            self.trace_rows += 1
        self.instrumentation.add(perf_counter_ns() - published)
        if self.metrics.counts["processed"] % 100 == 0:
            self.trace.flush()
            print(
                f"{self.config.mode}: source={observation / 1e9:.1f}s "
                f"updates={self.metrics.counts['processed']}",
                flush=True,
            )
        self.result = None


def run(
    config_path,
    output,
    mode,
    seconds,
    *,
    full_stack=True,
    trace_mode="COMPACT_ALPHA_TRACE",
    source_factory=VideoFileSource,
):
    import psutil

    output.mkdir(parents=True, exist_ok=False)
    base = config_path.resolve().parent
    raw = read_json(config_path)
    raw.update(
        mode=mode,
        start_ns=0,
        end_ns=int(seconds * 1e9),
        record_session=False,
        visualization=False,
        output=str(output.resolve()),
    )
    if mode == "OFFLINE_REPLAY":
        raw.update(drop_policy="PROCESS_ALL", max_staleness_ns=None)
    for key in (
        "world_model",
        "corridor",
        "trajectory",
        "interaction",
        "risk",
        "attention",
        "alerts",
    ):
        if full_stack and raw.get(key) is None:
            raw[key] = {}
    config = LabConfig.model_validate(raw)
    calibration = Calibration.model_validate(read_json(base / config.calibration))
    geometry = CoreGeometry(calibration, source_scaling=config.source_scaling)
    recorder = TraceRecorder(config, calibration, output)
    frozen = config.model_dump()
    for key in ("input", "calibration", "output"):
        frozen[key] = str((base / frozen[key]).resolve())
    for key in ("detector", "depth", "segmentation"):
        if frozen.get(key) and frozen[key].get("weights"):
            frozen[key]["weights"] = str((base / frozen[key]["weights"]).resolve())
    (output / "configuration.json").write_text(json.dumps(frozen, indent=2), encoding="utf-8")
    repository = Path(__file__).resolve().parents[1]
    runtime_sources = [
        *sorted((repository / "apps/perception-lab/src/perception_lab").glob("*.py")),
        Path(__file__).resolve(),
        repository / "tools/rescue_trace.py",
        repository / "tools/alpha_trace.py",
        repository / "tools/rescue_runtime.py",
        repository / "packages/guardian-core/target/guardian-core-0.1.0.jar",
    ]
    manifest = {
        "schema_version": 1,
        "status": "RUNNING",
        "mode": mode,
        "trace_mode": trace_mode,
        "source_sha256": digest(base / config.input),
        "calibration_sha256": digest(base / config.calibration),
        "configuration_sha256": digest(output / "configuration.json"),
        "runtime_source_sha256": {
            path.relative_to(repository).as_posix(): digest(path) for path in runtime_sources
        },
        "machine": {
            "platform": platform.platform(),
            "cpu": platform.processor(),
            "logical_cpus": psutil.cpu_count(),
            "ram": psutil.virtual_memory().total,
        },
        "python": platform.python_version(),
        "requested_seconds": seconds,
        "source_clock": "media PTS",
        "processing_clock": "perf_counter_ns",
        "offline_age_policy": "Wall source age unavailable; admission latency is not realtime age",
        "instrumentation": "Streamed per-update; 2048-value recent quantiles; 121 RSS samples",
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    source = None
    started = perf_counter_ns()
    try:
        detector = None
        if config.detector:
            d = config.detector
            factory = {"picodet": PicoDetDetector, "yolox": YoloXDetector}[d.runtime]
            detector = factory(
                base / d.weights,
                d.sha256,
                size=d.input_size,
                confidence=d.confidence,
                device=d.device,
                half=d.half,
                threads=d.threads,
            )
            manifest["detector_runtime"] = detector.runtime_metadata
        if config.entity_semantics_ontology is not None:
            if not isinstance(detector, PicoDetDetector):
                raise ValueError("Generic runtime semantic profile requires PicoDet")
            detector.enable_entity_semantics(base / config.entity_semantics_ontology)
        depth = None
        if config.depth:
            depth = (
                SyntheticDepthProvider(config.depth.synthetic_meters)
                if config.depth.provider == "synthetic"
                else DepthAnythingProvider(config.depth, base)
            )
        semantic = None
        if config.segmentation:
            semantic = (
                SyntheticSegmenter(recorder.session_id, config.segmentation.pattern)
                if config.segmentation.provider == "synthetic"
                else OnnxSemanticSegmenter(config.segmentation, base, recorder.session_id)
            )
        source = source_factory(base / config.input, config.source_id, config.max_pixels)
        with (output / "updates.jsonl").open("x", encoding="utf-8") as trace:
            writer = AsyncTrace(trace) if config.realtime_rescue else trace
            pipeline = TracePipeline(
                config,
                build_preprocessor(geometry, config),
                recorder,
                trace=writer,
                trace_mode=trace_mode,
                detector=detector,
                depth=depth,
                segmentation=semantic,
                motion_geometry=geometry,
            )
            try:
                result = pipeline.run(source)
            finally:
                if isinstance(writer, AsyncTrace):
                    writer.close()
                    manifest["trace_writer"] = {
                        "capacity": 16,
                        "peak": writer.peak,
                        "rows": writer.rows,
                        "dropped": 0,
                        "utf8_bytes": writer.utf8_bytes,
                        "serialization_ns": writer.serialization_ns,
                        "write_ns": writer.write_ns,
                    }
                else:
                    manifest["trace_writer"] = {
                        "capacity": 0,
                        "peak": 0,
                        "rows": pipeline.trace_rows,
                        "dropped": 0,
                        "utf8_bytes": pipeline.trace_bytes,
                        "serialization_ns": pipeline.serialization_ns,
                        "write_ns": pipeline.write_ns,
                    }
        source_end = (
            result["summary"].get("acquisition", {}).get("source_end_observed_ns")
            if config.realtime_rescue
            else pipeline.metrics.last_observation
        )
        complete = (
            result["termination_reason"] == "END_OF_STREAM"
            and result.get("failure") is None
            and result["summary"]["frame_counts"].get("failed", 0) == 0
            and source_end is not None
            and source_end >= (seconds - 1) * 1e9
        )
        manifest.update(
            status="COMPLETE" if complete else "INCOMPLETE",
            session=result,
            source_end_observed_ns=source_end,
            last_pipeline_observation_ns=pipeline.metrics.last_observation,
            elapsed_seconds=(perf_counter_ns() - started) / 1e9,
            update_intervals=pipeline.intervals.summary(),
            instrumentation=pipeline.instrumentation.summary(),
            memory={
                "start": pipeline.rss_start,
                "peak_sampled": pipeline.rss_peak,
                "end": pipeline.process_info.memory_info().rss,
                "samples": pipeline.rss_samples,
            },
        )
        if not complete:
            raise RuntimeError("Replay did not cover requested source interval")
    except BaseException as error:
        manifest.update(status="FAILED", error_type=type(error).__name__)
        raise
    finally:
        if source:
            source.close()
        recorder.close()
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=["REALTIME", "OFFLINE_REPLAY"], required=True)
    parser.add_argument("--seconds", type=float, default=600)
    parser.add_argument(
        "--trace-mode", choices=["COMPACT_ALPHA_TRACE", "FULL"], default="COMPACT_ALPHA_TRACE"
    )
    parser.add_argument("--ort-runtime", type=Path)
    parser.add_argument("--cuda-libraries", type=Path)
    parser.add_argument("--cudnn-directory", type=Path)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 3600:
        parser.error("seconds must be in [1, 3600]; longer runs require a separate reviewed budget")
    overrides = (args.ort_runtime, args.cuda_libraries, args.cudnn_directory)
    if any(overrides) and not all(overrides):
        parser.error("Isolated CUDA requires runtime, CUDA libraries and cuDNN directory together")
    directories = []
    try:
        if args.ort_runtime:
            from rescue_runtime import activate_onnx

            _, directories = activate_onnx(*overrides)
        run(args.config, args.output, args.mode, args.seconds, trace_mode=args.trace_mode)
    finally:
        for directory in directories:
            directory.close()
