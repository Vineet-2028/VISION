"""Pure reasoning timing on a bounded set of real, immutable WorldState snapshots."""

import argparse
import json
from pathlib import Path
from time import perf_counter_ns

from v0_analyze import quantiles
from world_benchmark import replay

from perception_lab.alerts import AlertEngine
from perception_lab.attention import NoveltyEscalationAttentionPolicy
from perception_lab.config import Calibration, LabConfig, read_json
from perception_lab.corridor import HybridCorridorAnalyzer
from perception_lab.geometry import CoreGeometry
from perception_lab.interaction import TrajectoryCorridorInteractionAnalyzer
from perception_lab.risk import RuleBasedRiskEngine
from perception_lab.trajectory import AdaptiveKinematicPredictor


class Capture:
    def __init__(self):
        self.states = []

    def render(self, frame, result, *metrics):
        if result.world_state is not None and len(self.states) < 16:
            self.states.append(result.world_state)

    def close(self):
        pass


def benchmark(config_path, output):
    output.mkdir(parents=True, exist_ok=False)
    raw = read_json(config_path)
    base = config_path.resolve().parent
    for key in ("input", "calibration", "output"):
        raw[key] = str((base / raw[key]).resolve())
    for key in ("detector", "depth", "segmentation"):
        if raw.get(key) and raw[key].get("weights"):
            raw[key]["weights"] = str((base / raw[key]["weights"]).resolve())
    raw.update(mode="OFFLINE_REPLAY", drop_policy="PROCESS_ALL", max_staleness_ns=None)
    for name in (
        "world_model",
        "corridor",
        "trajectory",
        "interaction",
        "risk",
        "attention",
        "alerts",
    ):
        raw[name] = raw.get(name) or {}
    path = output / "capture-config.json"
    path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    capture = Capture()
    capture_report = replay(path, 2, renderer=capture)
    if not capture.states:
        raise ValueError("No real WorldState captured")
    config = LabConfig.model_validate(raw)
    calibration = Calibration.model_validate(read_json(Path(config.calibration)))
    geometry = CoreGeometry(calibration, source_scaling=config.source_scaling)
    timings = {
        name: []
        for name in (
            "corridor",
            "trajectory",
            "interaction",
            "risk",
            "attention",
            "alerts",
            "total",
        )
    }
    for _ in range(20):
        corridor = HybridCorridorAnalyzer(config.corridor, geometry)
        trajectory = AdaptiveKinematicPredictor(config.trajectory, geometry)
        interaction = TrajectoryCorridorInteractionAnalyzer(config.interaction, geometry)
        risk = RuleBasedRiskEngine(config.risk)
        attention = NoveltyEscalationAttentionPolicy(config.attention)
        alerts = AlertEngine(config.alerts)
        try:
            for world in capture.states:
                start = last = perf_counter_ns()
                c = corridor.analyze(world)
                now = perf_counter_ns()
                timings["corridor"].append(now - last)
                last = now
                t = trajectory.predict(world, c)
                now = perf_counter_ns()
                timings["trajectory"].append(now - last)
                last = now
                i = interaction.analyze(world, c, t)
                now = perf_counter_ns()
                timings["interaction"].append(now - last)
                last = now
                r = risk.assess(world, c, t, i)
                now = perf_counter_ns()
                timings["risk"].append(now - last)
                last = now
                a = attention.decide(r, now_ns=world.state_timestamp)
                now = perf_counter_ns()
                timings["attention"].append(now - last)
                last = now
                alerts.process(a, now_ns=world.state_timestamp, mode="OFFLINE_REPLAY_PRESENTATION")
                now = perf_counter_ns()
                timings["alerts"].append(now - last)
                timings["total"].append(now - start)
        finally:
            risk.reset()
            attention.reset()
            alerts.reset()
    result = {
        "schema_version": 1,
        "snapshots": len(capture.states),
        "passes": 20,
        "updates": len(timings["total"]),
        "timing": {k: quantiles(v) for k, v in timings.items()},
        "throughput_updates_per_second": len(timings["total"]) * 1e9 / sum(timings["total"]),
        "capture": capture_report,
        "scope": "Repeated first 16 real snapshots; cached JVM; no inference; "
        "not deployment throughput",
    }
    (output / "summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    benchmark(args.config, args.output)
