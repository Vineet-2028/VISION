"""Bounded local world-model stress/replay measurements; never accuracy or risk scores."""

import argparse
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from time import perf_counter_ns

import psutil

from perception_lab.config import Calibration, LabConfig, read_json
from perception_lab.contracts import (
    ComponentProvenance,
    FrameIdentity,
    TimingProvenance,
)
from perception_lab.depth_runtime import DepthAnythingProvider
from perception_lab.depth_synthetic import SyntheticDepthProvider
from perception_lab.detection import Box, ObjectClass
from perception_lab.edge_runtime import PicoDetDetector, YoloXDetector
from perception_lab.geometry import CoreGeometry
from perception_lab.metrics import Distribution
from perception_lab.pipeline import Pipeline
from perception_lab.preprocessing import BasicPreprocessor
from perception_lab.recording import SessionRecorder
from perception_lab.semantic_runtime import OnnxSemanticSegmenter, SyntheticSegmenter
from perception_lab.sources import VideoFileSource
from perception_lab.tracking_types import (
    DetectorEvidence,
    Lifecycle,
    TrackId,
    TrackSet,
    TrackSnapshot,
)
from perception_lab.world_config import WorldModelConfig
from perception_lab.world_model import PrototypeWorldModel


class MeasuredWorld(PrototypeWorldModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.measurements = {
            k: Distribution(2048)
            for k in (
                "entity_update",
                "depth_update",
                "surface_update",
                "snapshot",
                "consume",
            )
        }
        self.ages = {
            k: Distribution(2048)
            for k in ("tracking", "depth", "motion", "pose", "semantics", "surface")
        }
        self.process = psutil.Process()
        self.start_rss = self.peak_rss = self.process.memory_info().rss
        self.memory_samples = []
        self.peak_history = self.peak_regions = self.partial = self.degraded = 0
        self.last_print = -1

    def ingest_tracks(self, *args):
        start = perf_counter_ns()
        super().ingest_tracks(*args)
        self.measurements["entity_update"].add(perf_counter_ns() - start)

    def ingest_depth(self, *args):
        start = perf_counter_ns()
        super().ingest_depth(*args)
        self.measurements["depth_update"].add(perf_counter_ns() - start)

    def ingest_surface(self, *args):
        start = perf_counter_ns()
        super().ingest_surface(*args)
        self.measurements["surface_update"].add(perf_counter_ns() - start)

    def snapshot(self, timestamp):
        start = perf_counter_ns()
        state = super().snapshot(timestamp)
        self.measurements["snapshot"].add(perf_counter_ns() - start)
        self.partial += any(c.status.value in {"UNAVAILABLE", "FAILED"} for c in state.capabilities)
        self.degraded += state.scene_quality.state != "GOOD"
        self.peak_history = max(self.peak_history, sum(len(e.history) for e in state.entities))
        self.peak_regions = max(self.peak_regions, len(state.surface_state.regions))
        for name, age in state.source_ages:
            if name in self.ages and age is not None:
                self.ages[name].add(age)
        rss = self.process.memory_info().rss
        self.peak_rss = max(self.peak_rss, rss)
        if len(self.memory_samples) < 121 and timestamp >= len(self.memory_samples) * 5_000_000_000:
            self.memory_samples.append(rss)
        if timestamp // 30_000_000_000 > self.last_print:
            self.last_print = timestamp // 30_000_000_000
            print(
                f"World source seconds={timestamp / 1e9:.1f}; snapshots={self.snapshots}",
                flush=True,
            )
        return state

    def consume(self, result):
        start = perf_counter_ns()
        state = super().consume(result)
        self.measurements["consume"].add(perf_counter_ns() - start)
        return state

    def report(self):
        return {
            "snapshots": self.snapshots,
            "created": self.created,
            "expired": self.expired,
            "peak_entities": self.peak_entities,
            "peak_history_entries": self.peak_history,
            "peak_regions": self.peak_regions,
            "partial_states": self.partial,
            "degraded_states": self.degraded,
            "timing": {k: v.summary() for k, v in self.measurements.items()},
            "source_ages": {k: v.summary() for k, v in self.ages.items()},
            "memory": {
                "start_rss": self.start_rss,
                "peak_sampled_rss": self.peak_rss,
                "end_rss": self.process.memory_info().rss,
                "samples": self.memory_samples,
            },
            "limits": self.config.model_dump(),
            "measurement_scope": (
                "consume includes benchmark counters/RSS sampling; "
                "stage timings exclude that instrumentation"
            ),
        }


def replay(
    config_path,
    seconds,
    corridor_factory=None,
    renderer=None,
    trajectory_factory=None,
    interaction_factory=None,
    risk_factory=None,
    attention_factory=None,
    source_transform=None,
    alert_factory=None,
):
    base = config_path.resolve().parent
    raw = read_json(config_path)
    raw.update(
        world_model=raw.get("world_model", {}),
        end_ns=seconds * 1_000_000_000,
        visualization=False,
        record_session=False,
    )
    config = LabConfig.model_validate(raw)
    if corridor_factory is not None:
        config = LabConfig.model_validate({**config.model_dump(), "corridor": {}})
    if trajectory_factory is not None:
        config = LabConfig.model_validate({**config.model_dump(), "trajectory": {}})
    if interaction_factory is not None:
        config = LabConfig.model_validate({**config.model_dump(), "interaction": {}})
    if risk_factory is not None:
        config = LabConfig.model_validate({**config.model_dump(), "risk": {}})
    if attention_factory is not None:
        config = LabConfig.model_validate({**config.model_dump(), "attention": {}})
    if alert_factory is not None:
        config = LabConfig.model_validate({**config.model_dump(), "alerts": {}})
    calibration = Calibration.model_validate(read_json(base / config.calibration))
    geometry = CoreGeometry(calibration, source_scaling=config.source_scaling)
    recorder = SessionRecorder(config, calibration, base / config.output)
    source = VideoFileSource(base / config.input, config.source_id, config.max_pixels)
    world = MeasuredWorld(config.world_model, recorder.session_id, config.source_id, geometry)
    corridor = corridor_factory(config.corridor, geometry) if corridor_factory else None
    trajectory = trajectory_factory(config.trajectory, geometry) if trajectory_factory else None
    interaction = interaction_factory(config.interaction, geometry) if interaction_factory else None
    risk = risk_factory(config.risk) if risk_factory else None
    attention = attention_factory(config.attention) if attention_factory else None
    alerts = alert_factory(config.alerts) if alert_factory else None
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
        pipeline = Pipeline(
            config,
            BasicPreprocessor(geometry, config.preprocess),
            recorder,
            detector=detector,
            depth=depth,
            segmentation=semantic,
            motion_geometry=geometry,
            world_model=world,
            corridor_analyzer=corridor,
            trajectory_predictor=trajectory,
            interaction_analyzer=interaction,
            risk_engine=risk,
            attention_engine=attention,
            alert_engine=alerts,
            renderer=renderer,
        )
        started = perf_counter_ns()
        manifest = pipeline.run(source_transform(source) if source_transform else source)
        elapsed = (perf_counter_ns() - started) / 1e9
        if (
            manifest["termination_reason"] != "END_OF_STREAM"
            or pipeline.metrics.last_observation is None
            or pipeline.metrics.last_observation < (seconds - 1) * 1_000_000_000
        ):
            raise ValueError("Replay did not cover requested duration")
        with (base / config.input).open("rb") as stream:
            source_hash = hashlib.file_digest(stream, "sha256").hexdigest()
        return {
            "mode": config.mode,
            "source_sha256": source_hash,
            "source_end_ns": pipeline.metrics.last_observation,
            "wall_seconds": elapsed,
            "configuration": config.public_configuration(),
            "pipeline": manifest["summary"],
            "world": world.report(),
            "corridor": corridor.report() if corridor else None,
            "trajectory": trajectory.report() if trajectory else None,
            "interaction": interaction.report() if interaction else None,
            "risk": risk.report() if risk else None,
            "attention": attention.report() if attention else None,
            "alerts": alerts.report() if alerts else None,
            "semantic_validation": "UNVERIFIED",
            "metric_depth_validation": "UNVALIDATED",
            "scope": "Local replay engineering; no physical or semantic accuracy qualification",
        }
    finally:
        source.close()
        world.close()
        recorder.close()


def stress():
    provenance = ComponentProvenance("synthetic-stress", "tracker")
    results = []
    for count in (1, 10, 50, 100, 129):
        world = PrototypeWorldModel(WorldModelConfig(), "stress", "synthetic")
        update, snapshot = Distribution(2048), Distribution(2048)
        track = TrackSnapshot(
            TrackId("stress", 1),
            Lifecycle.CONFIRMED,
            "OBSERVED",
            ObjectClass.PERSON,
            0.9,
            Box(0, 0, 2, 3),
            Box(0, 0, 2, 3),
            Box(0, 0, 2, 3),
            0,
            0,
            0,
            0,
            1,
            0,
            1,
            0,
            0.9,
            0.8,
            (0.0, 0.0),
            0.0,
            (),
            provenance,
            None,
        )
        start_rss = psutil.Process().memory_info().rss
        peak_history = 0
        for index in range(2000):
            ns = index * 33_333_333
            identity = FrameIdentity("synthetic", index, ns, TimingProvenance.SYNTHETIC)
            items = tuple(
                replace(
                    track,
                    track_id=TrackId("stress", i + 1),
                    latest_observed_ns=ns,
                    state_ns=ns,
                )
                for i in range(count)
            )
            batch = TrackSet(
                "stress", identity, items, (), DetectorEvidence.SUCCESS, (), provenance
            )
            started = perf_counter_ns()
            world.ingest_tracks(batch, ns)
            middle = perf_counter_ns()
            state = world.snapshot(ns)
            ended = perf_counter_ns()
            update.add(middle - started)
            snapshot.add(ended - middle)
            peak_history = max(peak_history, sum(len(e.history) for e in state.entities))
        results.append(
            {
                "input_entities": count,
                "updates": 2000,
                "retained_entities": len(state.entities),
                "peak_history_entries": peak_history,
                "created": world.created,
                "update": update.summary(),
                "snapshot": snapshot.summary(),
                "rss_start": start_rss,
                "rss_end": psutil.Process().memory_info().rss,
            }
        )
        world.close()
        print(f"Stress entities={count} complete", flush=True)
    return {
        "scope": "synthetic contract load, not perception accuracy",
        "results": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--seconds", type=int, choices=range(1, 601), default=600)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a new output; preserve previous measurements")
    report = replay(args.config, args.seconds) if args.config else stress()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
