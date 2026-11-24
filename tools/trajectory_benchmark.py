"""Bounded causal research evaluation. Tracker futures are proxies, not reviewed truth."""

import argparse
import json
from collections import Counter, deque
from dataclasses import replace
from math import dist
from pathlib import Path
from time import perf_counter_ns

import cv2
import psutil
from corridor_benchmark import MeasuredCorridor
from world_benchmark import replay

from perception_lab.config import Calibration, read_json
from perception_lab.contracts import ComponentProvenance, FrameIdentity, TimingProvenance
from perception_lab.corridor_overlay import draw_corridor
from perception_lab.detection import Box, ObjectClass
from perception_lab.geometry import CoreGeometry
from perception_lab.metrics import Distribution
from perception_lab.tracking_types import (
    DetectorEvidence,
    Lifecycle,
    TrackId,
    TrackSet,
    TrackSnapshot,
)
from perception_lab.trajectory import AdaptiveKinematicPredictor
from perception_lab.trajectory_config import TrajectoryConfig
from perception_lab.trajectory_fit import linear_fit
from perception_lab.trajectory_overlay import draw_trajectories
from perception_lab.trajectory_types import TrajectoryDomain
from perception_lab.world_config import WorldModelConfig
from perception_lab.world_model import PrototypeWorldModel
from perception_lab.world_types import EvidenceSource, EvidenceStatus, WorldImageGeometry


def fixture(count=1):
    p = ComponentProvenance("synthetic-independent", "tracker")
    world = PrototypeWorldModel(WorldModelConfig(max_entities=512), "stress", "synthetic")
    for i in range(16):
        t = i * 100_000_000
        ident = FrameIdentity("synthetic", i, t, TimingProvenance.SYNTHETIC)
        box = Box(300 + i, 200, 340 + i, 460)
        item = TrackSnapshot(
            TrackId("stress", 1),
            Lifecycle.CONFIRMED,
            "OBSERVED",
            ObjectClass.PERSON,
            0.9,
            box,
            box,
            box,
            t,
            t,
            t,
            0,
            i + 1,
            0,
            i + 1,
            0,
            0.9,
            0.8,
            (10.0, 0.0),
            0.0,
            (),
            p,
            None,
        )
        world.ingest_tracks(
            TrackSet(
                "stress",
                ident,
                tuple(replace(item, track_id=TrackId("stress", j + 1)) for j in range(count)),
                (),
                DetectorEvidence.SUCCESS,
                (),
                p,
            ),
            t,
        )
    state = replace(
        world.snapshot(t),
        image_geometry=WorldImageGeometry(
            "image",
            640,
            480,
            EvidenceSource(
                "camera", ident, 0, EvidenceStatus.FRESH, "OBSERVED", "DEGRADED", "UNVERIFIED"
            ),
        ),
    )
    world.close()
    return state


class MeasuredTrajectory(AdaptiveKinematicPredictor):
    def __init__(self, *args, evaluate=False):
        super().__init__(*args)
        self.timing = Distribution(2048)
        self.intervals = Distribution(2048)
        self.last = None
        self.models, self.quality, self.domains = Counter(), Counter(), Counter()
        self.unavailable = 0
        self.pending = deque(maxlen=65536)
        self.last_evaluation_ns = -250_000_000
        self.errors = {}
        self.expired = self.overflow = 0
        self.evaluate = evaluate
        self.comparators = (
            [
                AdaptiveKinematicPredictor(TrajectoryConfig(model=m), self.geometry)
                for m in ("CONSTANT_POSITION", "CV_LAST_TWO", "CV_WINDOW")
            ]
            if evaluate
            else []
        )

    def predict(self, state, corridor=None):
        started = perf_counter_ns()
        result = super().predict(state, corridor)
        self.timing.add(perf_counter_ns() - started)
        if self.last is not None:
            self.intervals.add(state.state_timestamp - self.last)
        self.last = state.state_timestamp
        self.models.update(t.model for t in result.trajectories)
        self.quality.update(t.quality for t in result.trajectories)
        self.domains.update(t.coordinate_space.value for t in result.trajectories)
        self.unavailable += len(result.unavailable)
        if self.evaluate:
            self.score(state)
            if state.state_timestamp - self.last_evaluation_ns < 250_000_000:
                return result
            self.last_evaluation_ns = state.state_timestamp
            outputs = [
                ("ADAPTIVE", result),
                *((p.config.model, p.predict(state)) for p in self.comparators),
            ]
            for model, output in outputs:
                for t in output.trajectories:
                    if t.coordinate_space != TrajectoryDomain.IMAGE:
                        continue
                    label = "RESIDUAL" if t.motion_basis != "OBSERVED_HISTORY" else model
                    if label == "RESIDUAL" and model != "ADAPTIVE":
                        continue
                    for s in t.samples:
                        if len(self.pending) == self.pending.maxlen:
                            self.overflow += 1
                        self.pending.append(
                            (t.entity_id, label, s.horizon_ns, s.timestamp_ns, s.position)
                        )
        return result

    def score(self, state):
        observed = {
            e.entity_id: ((e.image_geometry.x1 + e.image_geometry.x2) / 2, e.image_geometry.y2)
            for e in state.entities
            if e.observation_status == "OBSERVED" and e.latest_observed_ns == state.state_timestamp
        }
        for _ in range(len(self.pending)):
            item = self.pending.popleft()
            entity, model, horizon, target, prediction = item
            delta = state.state_timestamp - target
            if delta > 100_000_000:
                self.expired += 1
            elif delta >= 0 and entity in observed:
                key = f"{model}:{horizon}"
                entry = self.errors.setdefault(
                    key,
                    {
                        "count": 0,
                        "sum_error_pixels": 0.0,
                        "max_error_pixels": 0.0,
                        "sum_match_offset_ns": 0,
                    },
                )
                error = dist(prediction, observed[entity])
                entry["count"] += 1
                entry["sum_error_pixels"] += error
                entry["max_error_pixels"] = max(entry["max_error_pixels"], error)
                entry["sum_match_offset_ns"] += delta
            else:
                self.pending.append(item)

    def report(self):
        return {
            "updates": self.timing.count,
            "compute": self.timing.summary(),
            "arrival_intervals": self.intervals.summary(),
            "models": dict(self.models),
            "quality": dict(self.quality),
            "domains": dict(self.domains),
            "unavailable_domain_or_entity": self.unavailable,
            "retrospective": self.errors,
            "expired": self.expired,
            "pending_end": len(self.pending),
            "overflow": self.overflow,
            "prediction_sampling_ns": 250_000_000,
            "pending_capacity": self.pending.maxlen,
            "truth_status": "FUTURE_TRACKER_OBSERVATION_PROXY_NOT_INDEPENDENT_TRUTH",
            "matching": (
                "Same WorldEntityId; first observation at or after target, at most 100ms late; "
                "residual comparison is raw-view mismatch diagnostic only"
            ),
        }


class DebugFrames:
    def __init__(self, directory):
        directory.mkdir(parents=True, exist_ok=False)
        self.directory, self.count = directory, 0

    def render(self, frame, result, source_fps, processing_fps):
        if (
            self.count >= 8
            or frame.identity.observation_ns < self.count * 500_000_000
            or result.trajectory_set is None
        ):
            return
        pixels = frame.pixels
        if result.corridor_analysis is not None:
            pixels = draw_corridor(pixels, result.world_state, result.corridor_analysis)
        pixels = draw_trajectories(pixels, result.trajectory_set)
        if not cv2.imwrite(
            str(self.directory / f"trajectory-{self.count}.png"),
            cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR),
        ):
            raise ValueError("Debug write failed")
        self.count += 1

    def close(self):
        pass


def synthetic():
    results = []
    horizons = (0.25, 0.5, 1.0, 1.5, 2.0, 3.0)
    for case in (
        "stationary",
        "horizontal",
        "vertical",
        "diagonal",
        "acceleration",
        "noisy",
        "outlier",
        "irregular",
    ):
        times = tuple((i / 10 if case != "irregular" else i * i / 150) for i in range(16))

        def truth(t, case=case):
            return (
                0.0
                if case in {"stationary", "vertical"}
                else 10 * t + (2 * t * t if case == "acceleration" else 0.0),
                5 * t if case in {"vertical", "diagonal"} else 0.0,
            )

        points = tuple(
            (
                truth(t)[0]
                + (
                    (0.8 if i % 2 else -0.8)
                    if case == "noisy"
                    else 500.0
                    if case == "outlier" and i == 9
                    else 0.0
                ),
                truth(t)[1],
            )
            for i, t in enumerate(times)
        )
        for model in ("CP", "CV_LAST_TWO", "CV_WINDOW"):
            fit = linear_fit(times, points, 2.0, 4.0, model == "CV_LAST_TWO")
            p, v = (points[-1], (0.0, 0.0)) if model == "CP" else (fit.position, fit.velocity)
            errors = [
                dist(tuple(a + b * h for a, b in zip(p, v, strict=True)), truth(times[-1] + h))
                for h in horizons
            ]
            results.append(
                {
                    "case": case,
                    "model": model,
                    "units": "pixels",
                    "horizons_seconds": horizons,
                    "errors": errors,
                    "ADE": sum(errors) / len(errors),
                    "FDE": errors[-1],
                }
            )
    stress = []
    for count in (1, 10, 50, 100, 128, 512):
        state, predictor = fixture(count), AdaptiveKinematicPredictor(TrajectoryConfig())
        timing, process = Distribution(2048), psutil.Process()
        start = process.memory_info().rss
        for _ in range(200):
            at = perf_counter_ns()
            predictor.predict(state)
            timing.add(perf_counter_ns() - at)
        stress.append(
            {
                "entities": count,
                "history": 16,
                "timing": timing.summary(),
                "rss_start": start,
                "rss_end": process.memory_info().rss,
            }
        )
    return {
        "synthetic": results,
        "world_synthetic": world_synthetic(),
        "stress": stress,
        "CA": "DEFERRED: noisy short histories/identity fragmentation do not justify acceleration",
    }


def world_synthetic():
    """Guardian nominal 3D output with synthetic research-meter truth, not sensor truth."""
    geometry = CoreGeometry(
        Calibration.model_validate(
            read_json(
                Path(__file__).resolve().parents[1] / "configs/calibration.synthetic.example.json"
            )
        )
    )
    times = tuple(i / 10 for i in range(16))
    horizons = TrajectoryConfig().horizons_ns
    results = []
    for noisy in (False, True):
        points = tuple(
            (t, 2 * t, 3 * t + ((0.2 if i % 2 else -0.2) if noisy else 0.0))
            for i, t in enumerate(times)
        )
        for model in ("CP", "CV_LAST_TWO", "CV_WINDOW"):
            fit = linear_fit(times, points, 0.25, 4.0, model == "CV_LAST_TWO")
            p, v = (points[-1], (0.0, 0.0, 0.0)) if model == "CP" else (fit.position, fit.velocity)
            future = geometry.predict_world_points(
                "synthetic-world", "synthetic", 1_500_000_000, p, v, horizons
            )
            errors = [
                dist(point, (1.5 + h / 1e9, 2 * (1.5 + h / 1e9), 3 * (1.5 + h / 1e9)))
                for point, h in zip(future, horizons, strict=True)
            ]
            results.append(
                {
                    "case": "depth-jitter" if noisy else "linear-xyz",
                    "model": model,
                    "units": "synthetic_meters",
                    "errors": errors,
                    "ADE": sum(errors) / len(errors),
                    "FDE": errors[-1],
                    "physical_truth": False,
                }
            )
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path)
    parser.add_argument("--seconds", type=int, default=600, choices=range(1, 601))
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--overlays", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Refusing to overwrite evidence")
    result = (
        replay(
            args.config,
            args.seconds,
            MeasuredCorridor,
            DebugFrames(args.overlays) if args.overlays else None,
            lambda *a: MeasuredTrajectory(*a, evaluate=args.evaluate),
        )
        if args.config
        else synthetic()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
