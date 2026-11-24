"""Task014 bounded measurements; future tracker observations are not physical truth."""

import argparse
import json
from collections import Counter, deque
from dataclasses import asdict
from pathlib import Path
from time import perf_counter_ns

import cv2
import psutil
from corridor_benchmark import MeasuredCorridor
from trajectory_benchmark import MeasuredTrajectory, fixture
from world_benchmark import replay

from perception_lab.config import Calibration, read_json
from perception_lab.corridor import HybridCorridorAnalyzer
from perception_lab.corridor_config import CorridorConfig
from perception_lab.corridor_overlay import draw_corridor
from perception_lab.geometry import CoreGeometry
from perception_lab.interaction import TrajectoryCorridorInteractionAnalyzer
from perception_lab.interaction_config import InteractionConfig
from perception_lab.interaction_geometry import segment, unsigned_distance
from perception_lab.interaction_overlay import draw_interactions
from perception_lab.metrics import Distribution
from perception_lab.trajectory import AdaptiveKinematicPredictor
from perception_lab.trajectory_config import TrajectoryConfig
from perception_lab.trajectory_overlay import draw_trajectories


class MeasuredInteraction(TrajectoryCorridorInteractionAnalyzer):
    def __init__(self, *args, evaluate=False):
        super().__init__(*args)
        self.evaluate = evaluate
        self.timing, self.arrivals = Distribution(2048), Distribution(2048)
        self.recording = Distribution(2048)
        self.last = None
        self.types, self.quality, self.ttc, self.cpa, self.envelopes = (Counter() for _ in range(5))
        self.categories = Counter()
        self.pending = deque(maxlen=4096)
        self.last_prediction = -250_000_000
        self.events = Counter()
        self.timing_error_sum = 0.0
        self.timing_error_count = 0
        self.distance_error_sum = 0.0
        self.evaluated = self.censored = self.overflow = 0
        self.previous_ids = set()
        self.identity_disappearances = 0
        self.examples = []

    def analyze(self, state, corridor, trajectories, reference=None):
        start = perf_counter_ns()
        result = super().analyze(state, corridor, trajectories, reference)
        self.timing.add(perf_counter_ns() - start)
        if self.last is not None:
            self.arrivals.add(state.state_timestamp - self.last)
        self.last = state.state_timestamp
        ids = {e.entity_id for e in state.entities}
        self.identity_disappearances += len(self.previous_ids - ids)
        self.previous_ids = ids
        self.types.update(r.interaction_type for r in result.entity_interactions)
        self.quality.update(r.quality for r in result.entity_interactions)
        self.ttc.update(r.ttc.status for r in result.entity_interactions)
        self.cpa.update(r.cpa.status for r in result.entity_interactions)
        self.envelopes.update(r.envelope_interaction for r in result.entity_interactions)
        categories = {e.entity_id: e.category.value for e in state.entities}
        self.categories.update(categories[r.entity_id] for r in result.entity_interactions)
        if self.evaluate:
            self._score(state)
            entity_by_id = {e.entity_id: e for e in state.entities}
            if state.state_timestamp - self.last_prediction >= 250_000_000:
                self.last_prediction = state.state_timestamp
                for r in result.entity_interactions:
                    if (
                        r.physical_validity.value != "IMAGE_GEOMETRIC"
                        or r.closest_corridor_approach is None
                        or r.quality == "UNAVAILABLE"
                    ):
                        continue
                    entity = entity_by_id[r.entity_id]
                    point = (
                        (entity.image_geometry.x1 + entity.image_geometry.x2) / 2,
                        entity.image_geometry.y2,
                    )
                    if (
                        entity.observation_status != "OBSERVED"
                        or entity.latest_observed_ns != state.state_timestamp
                        or unsigned_distance(point, corridor.corridor.image_polygon) == 0
                    ):
                        continue
                    if len(self.pending) == self.pending.maxlen:
                        self.overflow += 1
                        continue
                    self.pending.append(
                        {
                            "entity": r.entity_id,
                            "start": state.state_timestamp,
                            "end": state.state_timestamp + r.horizon_ns,
                            "polygon": corridor.corridor.image_polygon,
                            "predicted_entry": r.predicted_corridor_entry_time_ns,
                            "predicted_min": r.closest_corridor_approach.distance,
                            "last_time": state.state_timestamp,
                            "last_point": point,
                            "entry": None,
                            "minimum": unsigned_distance(point, corridor.corridor.image_polygon),
                            "max_gap": 0,
                            "observations": 0,
                        }
                    )
        if len(self.examples) < 8 and state.state_timestamp >= len(self.examples) * 1_000_000_000:
            begin = perf_counter_ns()
            example = asdict(result)
            json.dumps(example, allow_nan=False)
            self.recording.add(perf_counter_ns() - begin)
            self.examples.append(example)
        return result

    def _score(self, state):
        observed = {
            e.entity_id: e
            for e in state.entities
            if e.observation_status == "OBSERVED" and e.latest_observed_ns == state.state_timestamp
        }
        for _ in range(len(self.pending)):
            item = self.pending.popleft()
            now = state.state_timestamp
            e = observed.get(item["entity"])
            if e is not None and now <= item["end"]:
                p = (
                    (e.image_geometry.x1 + e.image_geometry.x2) / 2,
                    e.image_geometry.y2,
                )
                hit, distance, _ = segment(item["last_point"], p, item["polygon"])
                gap = now - item["last_time"]
                item["max_gap"] = max(item["max_gap"], gap)
                if hit is not None and item["entry"] is None:
                    item["entry"] = item["last_time"] - item["start"] + round(hit[0] * gap)
                item["minimum"] = min(item["minimum"], distance)
                item["last_time"], item["last_point"] = now, p
                item["observations"] += 1
            if now < item["end"]:
                self.pending.append(item)
                continue
            if (
                item["observations"] == 0
                or item["end"] - item["last_time"] > 100_000_000
                or item["max_gap"] > 250_000_000
            ):
                self.censored += 1
                continue
            predicted, actual = (
                item["predicted_entry"] is not None,
                item["entry"] is not None,
            )
            self.events[
                "TP" if predicted and actual else "FP" if predicted else "FN" if actual else "TN"
            ] += 1
            self.evaluated += 1
            self.on_evaluated(item, predicted, actual)
            self.distance_error_sum += abs(item["minimum"] - item["predicted_min"])
            if predicted and actual:
                self.timing_error_sum += abs(item["entry"] - item["predicted_entry"]) / 1e9
                self.timing_error_count += 1

    def on_evaluated(self, item, predicted, actual):
        """Optional downstream evaluation hook; never changes interaction predictions."""

    def report(self):
        tp, fp, fn = (self.events[k] for k in ("TP", "FP", "FN"))
        return {
            "updates": self.timing.count,
            "compute": self.timing.summary(),
            "arrival_intervals": self.arrivals.summary(),
            "sampled_serialization": self.recording.summary(),
            "types": dict(self.types),
            "quality": dict(self.quality),
            "ttc_status": dict(self.ttc),
            "cpa_status": dict(self.cpa),
            "envelopes": dict(self.envelopes),
            "category_hypotheses": dict(self.categories),
            "identity_disappearances": self.identity_disappearances,
            "retrospective": {
                "events": dict(self.events),
                "evaluated": self.evaluated,
                "censored": self.censored,
                "pending_end": len(self.pending),
                "overflow": self.overflow,
                "entry_precision": tp / (tp + fp) if tp + fp else None,
                "entry_recall": tp / (tp + fn) if tp + fn else None,
                "entry_timing_mae_seconds": self.timing_error_sum / self.timing_error_count
                if self.timing_error_count
                else None,
                "timing_sample_count": self.timing_error_count,
                "min_distance_mae_pixels": self.distance_error_sum / self.evaluated
                if self.evaluated
                else None,
                "reference": (
                    "FUTURE_TRACKER_PROXY; FROZEN_PREDICTION_TIME_CORRIDOR; NOT_REVIEWED_TRUTH"
                ),
                "coverage": (
                    "same identity, <=250ms gaps "
                    "(200ms configured detector cadence plus tolerance), "
                    "within100ms of horizon; incomplete windows censored"
                ),
            },
            "examples": self.examples,
        }


class DebugFrames:
    def __init__(self, directory):
        directory.mkdir(parents=True, exist_ok=False)
        self.directory, self.count = directory, 0

    def render(self, frame, result, source_fps, processing_fps):
        if (
            self.count >= 8
            or result.interaction_analysis is None
            or frame.identity.observation_ns < self.count * 1_000_000_000
        ):
            return
        pixels = draw_corridor(frame.pixels, result.world_state, result.corridor_analysis)
        pixels = draw_trajectories(pixels, result.trajectory_set)
        pixels = draw_interactions(pixels, result.interaction_analysis)
        path = self.directory / f"interaction-{self.count}.png"
        if not cv2.imwrite(str(path), cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR)):
            raise OSError("Unable to write debug overlay")
        self.count += 1

    def close(self):
        pass


def stress():
    output = []
    process = psutil.Process()
    for count in (1, 10, 50, 100, 128, 512):
        state = fixture(count)
        corridor = HybridCorridorAnalyzer(CorridorConfig()).analyze(state)
        ts = AdaptiveKinematicPredictor(TrajectoryConfig()).predict(state, corridor)
        engine = TrajectoryCorridorInteractionAnalyzer(InteractionConfig())
        timing = Distribution(2048)
        start = process.memory_info().rss
        for _ in range(200):
            begin = perf_counter_ns()
            engine.analyze(state, corridor, ts)
            timing.add(perf_counter_ns() - begin)
        output.append(
            {
                "entities": count,
                "timing": timing.summary(),
                "start_rss": start,
                "end_rss": process.memory_info().rss,
            }
        )
    geometry = CoreGeometry(
        Calibration.model_validate(read_json(Path("configs/calibration.synthetic.example.json")))
    )
    cases = []
    for name, p, v in (
        ("head_on", (0.0, 10.0, 0.0), (0.0, -2.0, 0.0)),
        ("side_pass", (2.0, 10.0, 0.0), (0.0, -2.0, 0.0)),
        ("receding", (0.0, 10.0, 0.0), (0.0, 2.0, 0.0)),
        ("static", (0.0, 10.0, 0.0), (0.0, 0.0, 0.0)),
    ):
        timer = Distribution(2048)
        for _ in range(200):
            begin = perf_counter_ns()
            value = geometry.relative_motion("synthetic", p, v, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
            timer.add(perf_counter_ns() - begin)
        cases.append({"case": name, "result": asdict(value), "bridge": timer.summary()})
    return {
        "stress": output,
        "guardian_synthetic": cases,
        "scope": "Software mathematics only",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--seconds", type=int, default=15)
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--overlays", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a new output; preserve previous measurements")
    if args.seconds <= 0:
        raise ValueError("Positive duration required")
    if args.config:
        report = replay(
            args.config,
            args.seconds,
            corridor_factory=MeasuredCorridor,
            trajectory_factory=MeasuredTrajectory,
            interaction_factory=lambda c, g: MeasuredInteraction(c, g, evaluate=args.evaluate),
            renderer=DebugFrames(args.overlays) if args.overlays else None,
        )
    else:
        report = stress()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
