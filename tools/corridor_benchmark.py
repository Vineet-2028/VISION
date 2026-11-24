"""Task012 bounded compute measurements. No safety or perception accuracy scores."""

import argparse
import json
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path
from time import perf_counter_ns

import cv2
import psutil
from world_benchmark import replay

from perception_lab.contracts import (
    ComponentProvenance,
    FrameIdentity,
    TimingProvenance,
)
from perception_lab.corridor import HybridCorridorAnalyzer
from perception_lab.corridor_config import CorridorConfig
from perception_lab.corridor_overlay import draw_corridor
from perception_lab.detection import Box, ObjectClass
from perception_lab.metrics import Distribution
from perception_lab.tracking_types import (
    DetectorEvidence,
    Lifecycle,
    TrackId,
    TrackSet,
    TrackSnapshot,
)
from perception_lab.world_config import WorldModelConfig
from perception_lab.world_model import PrototypeWorldModel
from perception_lab.world_types import (
    EvidenceSource,
    EvidenceStatus,
    WorldImageGeometry,
)


class MeasuredCorridor(HybridCorridorAnalyzer):
    def __init__(self, *args):
        super().__init__(*args)
        self.timing, self.intervals = Distribution(2048), Distribution(2048)
        self.modes, self.relations, self.quality = Counter(), Counter(), Counter()
        self.last = None
        self.last_mode = None
        self.switches = 0
        self.process = psutil.Process()
        self.start_rss = self.peak_rss = self.process.memory_info().rss
        self.samples = []
        self.examples = []

    def analyze(self, state):
        started = perf_counter_ns()
        result = super().analyze(state)
        self.timing.add(perf_counter_ns() - started)
        if self.last is not None:
            self.intervals.add(state.state_timestamp - self.last)
        self.last = state.state_timestamp
        mode = result.corridor.mode.value
        self.switches += self.last_mode is not None and mode != self.last_mode
        self.last_mode = mode
        self.modes[mode] += 1
        self.quality[result.quality] += 1
        self.relations.update(r.relation.value for r in result.entity_relations)
        self.peak_rss = max(self.peak_rss, self.process.memory_info().rss)
        if len(self.samples) < 121 and state.state_timestamp >= len(self.samples) * 5_000_000_000:
            self.samples.append(self.process.memory_info().rss)
        if len(self.examples) < 8 and state.state_timestamp >= len(self.examples) * 1_000_000_000:
            self.examples.append(asdict(result))  # Bounded offline diagnostic serialization.
        return result

    def report(self):
        return {
            "analyses": self.timing.count,
            "compute": self.timing.summary(),
            "world_update_interval": self.intervals.summary(),
            "mode_counts": dict(self.modes),
            "mode_switches": self.switches,
            "relation_counts": dict(self.relations),
            "quality_counts": dict(self.quality),
            "memory": {
                "start_rss": self.start_rss,
                "peak_sampled_rss": self.peak_rss,
                "end_rss": self.process.memory_info().rss,
                "samples": self.samples,
            },
            "examples": self.examples,
            "scope": (
                "Compute excludes benchmark instrumentation; RSS is whole process including models"
            ),
        }


class DebugFrames:
    """Explicit local output only; at most eight frames, no network or overwrite."""

    def __init__(self, directory):
        directory.mkdir(exist_ok=False, parents=True)
        self.directory, self.count = directory, 0

    def render(self, frame, result, source_fps, processing_fps):
        if self.count >= 8 or frame.identity.observation_ns < self.count * 300_000_000:
            return
        if result.corridor_analysis is not None and result.world_state is not None:
            pixels = draw_corridor(frame.pixels, result.world_state, result.corridor_analysis)
            if not cv2.imwrite(
                str(self.directory / f"corridor-{self.count}.png"),
                cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR),
            ):
                raise ValueError("Debug image write failed")
            self.count += 1

    def close(self):
        pass


def stress():
    reports = []
    p = ComponentProvenance("synthetic", "tracker")
    for count in (1, 10, 50, 100, 128, 512):
        world = PrototypeWorldModel(WorldModelConfig(max_entities=512), "stress", "synthetic")
        ident = FrameIdentity("synthetic", 0, 0, TimingProvenance.SYNTHETIC)
        snapshot = TrackSnapshot(
            TrackId("stress", 1),
            Lifecycle.CONFIRMED,
            "OBSERVED",
            ObjectClass.PERSON,
            0.9,
            Box(300, 200, 340, 460),
            Box(300, 200, 340, 460),
            Box(300, 200, 340, 460),
            0,
            0,
            0,
            0,
            2,
            0,
            2,
            0,
            0.9,
            0.8,
            (0.0, 0.0),
            0.0,
            (),
            p,
            None,
        )
        tracks = tuple(replace(snapshot, track_id=TrackId("stress", i + 1)) for i in range(count))
        world.ingest_tracks(
            TrackSet("stress", ident, tracks, (), DetectorEvidence.SUCCESS, (), p), 0
        )
        state = replace(
            world.snapshot(0),
            image_geometry=WorldImageGeometry(
                "image",
                640,
                480,
                EvidenceSource(
                    "camera",
                    ident,
                    0,
                    EvidenceStatus.FRESH,
                    "OBSERVED",
                    "DEGRADED",
                    "UNVERIFIED",
                ),
            ),
        )
        analyzer = HybridCorridorAnalyzer(CorridorConfig())
        timing = Distribution(2048)
        process = psutil.Process()
        rss_start = process.memory_info().rss
        for _ in range(2000):
            start = perf_counter_ns()
            result = analyzer.analyze(state)
            timing.add(perf_counter_ns() - start)
            assert len(result.entity_relations) == count
        reports.append(
            {
                "entities": count,
                "timing": timing.summary(),
                "rss_start": rss_start,
                "rss_end": process.memory_info().rss,
            }
        )
        world.close()
        print(f"Stress {count} complete", flush=True)
    return {"scope": "synthetic immutable WorldState, compute only", "results": reports}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--seconds", type=int, choices=range(1, 601), default=600)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overlays", type=Path, help="Opt-in private bounded debug PNG directory")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Preserve previous evidence; choose new output")
    renderer = DebugFrames(args.overlays) if args.overlays else None
    result = (
        replay(args.config, args.seconds, MeasuredCorridor, renderer) if args.config else stress()
    )
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
