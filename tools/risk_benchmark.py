"""Bounded Task015 measurements. Tracker proxies are not reviewed hazard truth."""

import argparse
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from time import perf_counter_ns

import cv2
import psutil
from corridor_benchmark import MeasuredCorridor
from interaction_benchmark import MeasuredInteraction
from trajectory_benchmark import MeasuredTrajectory, fixture
from world_benchmark import replay

from perception_lab.corridor import HybridCorridorAnalyzer
from perception_lab.corridor_config import CorridorConfig
from perception_lab.interaction import TrajectoryCorridorInteractionAnalyzer
from perception_lab.interaction_config import InteractionConfig
from perception_lab.metrics import Distribution
from perception_lab.risk import RuleBasedRiskEngine
from perception_lab.risk_config import RiskConfig
from perception_lab.risk_overlay import draw_risk
from perception_lab.risk_types import RiskLevel
from perception_lab.trajectory import AdaptiveKinematicPredictor
from perception_lab.trajectory_config import TrajectoryConfig


class ProxyInteraction(MeasuredInteraction):
    def __init__(self, *args, evaluate=False):
        super().__init__(*args, evaluate=evaluate)
        self.risk_events = Counter()
        self.conditional = Counter()
        self.sensitivity_events = [Counter() for _ in range(3)]

    def on_evaluated(self, item, predicted, actual):
        raised = item.get("risk") in {"ELEVATED", "HIGH", "SEVERE"}
        self.risk_events[
            "TP" if raised and actual else "FP" if raised else "FN" if actual else "TN"
        ] += 1
        if actual:
            self.conditional["proxy_relevant"] += 1
            self.conditional["interaction_predicted"] += int(predicted)
            self.conditional["risk_raised"] += int(raised)
            self.conditional["risk_raised_given_interaction"] += int(predicted and raised)
        for counts, level in zip(
            self.sensitivity_events, item.get("sensitivity", []), strict=False
        ):
            high = level in {"ELEVATED", "HIGH", "SEVERE"}
            counts["TP" if high and actual else "FP" if high else "FN" if actual else "TN"] += 1

    def report(self):
        return {
            **super().report(),
            "risk_proxy_events": dict(self.risk_events),
            "coverage_funnel": {
                "source_reviewed_events": None,
                "events_missed_by_detector_tracker": None,
                "reference": "OBSERVED_SAME_ID_TRACKER_WINDOWS; SELECTION_BIASED",
                **dict(self.conditional),
            },
            "sensitivity_events": [dict(c) for c in self.sensitivity_events],
        }


class MeasuredRisk(RuleBasedRiskEngine):
    def __init__(self, config, proxy=None, sensitivity=False):
        super().__init__(config)
        self.proxy = proxy
        self.timer = Distribution(2048)
        self.serialization = Distribution(64)
        self.levels, self.qualities, self.reasons, self.classes = (Counter() for _ in range(4))
        self.peak_history = 0
        self.examples = []
        self.variants = (
            [
                RuleBasedRiskEngine(RiskConfig(urgent_entry_ns=n))
                for n in (500_000_000, 1_000_000_000, 2_000_000_000)
            ]
            if sensitivity
            else []
        )
        self.variant_levels = [Counter() for _ in self.variants]

    def assess(self, state, corridor, trajectories, interaction):
        start = perf_counter_ns()
        result = super().assess(state, corridor, trajectories, interaction)
        self.timer.add(perf_counter_ns() - start)
        self.peak_history = max(self.peak_history, self.history_size)
        self.levels.update(a.risk_level for a in result.assessments)
        self.qualities.update(a.evidence_quality for a in result.assessments)
        self.reasons.update(r for a in result.assessments for r in a.reason_codes)
        categories = {e.entity_id: e.category.value for e in state.entities}
        self.classes.update(f"{categories[a.entity_id]}:{a.risk_level}" for a in result.assessments)
        variants = [
            engine.assess(state, corridor, trajectories, interaction) for engine in self.variants
        ]
        for counts, output in zip(self.variant_levels, variants, strict=True):
            counts.update(a.risk_level for a in output.assessments)
        if self.proxy is not None and self.proxy.evaluate:
            levels = {a.entity_id: a.risk_level for a in result.assessments}
            alternatives = [{a.entity_id: a.risk_level for a in v.assessments} for v in variants]
            for item in self.proxy.pending:
                if item["start"] == state.state_timestamp:
                    item["risk"] = levels.get(item["entity"], RiskLevel.UNDETERMINED)
                    item["sensitivity"] = [
                        v.get(item["entity"], RiskLevel.UNDETERMINED) for v in alternatives
                    ]
        if len(self.examples) < 8 and state.state_timestamp >= len(self.examples) * 1_000_000_000:
            start = perf_counter_ns()
            example = asdict(result)
            json.dumps(example, allow_nan=False)
            self.serialization.add(perf_counter_ns() - start)
            self.examples.append(example)
        return result

    def report(self):
        return {
            "updates": self.timer.count,
            "compute": self.timer.summary(),
            "sampled_serialization": self.serialization.summary(),
            "levels": dict(self.levels),
            "quality": dict(self.qualities),
            "reasons": dict(self.reasons),
            "class_levels": dict(self.classes),
            "peak_history": self.peak_history,
            "config_hash": self.config_hash,
            "configuration": self.config.model_dump(),
            "sensitivity_levels": [dict(c) for c in self.variant_levels],
            "examples": self.examples,
            "risk_ground_truth_validated": False,
        }


class DebugRisk:
    def __init__(self, directory):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=False)
        self.count = 0

    def render(self, frame, result, source_fps, processing_fps):
        if self.count >= 8 or result.risk_assessment_set is None:
            return
        if result.identity.observation_ns < self.count * 1_000_000_000:
            return
        pixels = draw_risk(frame.pixels, result.risk_assessment_set)
        if not cv2.imwrite(
            str(self.directory / f"risk-{self.count}.png"), cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR)
        ):
            raise OSError("Unable to write risk debug image")
        self.count += 1

    def close(self):
        pass


def stress():
    results = []
    process = psutil.Process()
    for count in (1, 10, 50, 100, 128, 512):
        s = fixture(count)
        c = HybridCorridorAnalyzer(CorridorConfig()).analyze(s)
        t = AdaptiveKinematicPredictor(TrajectoryConfig()).predict(s, c)
        i = TrajectoryCorridorInteractionAnalyzer(InteractionConfig()).analyze(s, c, t)
        engine = RuleBasedRiskEngine(RiskConfig())
        timer = Distribution(2048)
        initial = process.memory_info().rss
        for _ in range(200):
            begin = perf_counter_ns()
            result = engine.assess(s, c, t, i)
            timer.add(perf_counter_ns() - begin)
        assert len(result.assessments) == count and engine.history_size == count
        results.append(
            {
                "entities": count,
                "timing": timer.summary(),
                "history": engine.history_size,
                "rss_start": initial,
                "rss_end": process.memory_info().rss,
            }
        )
    return {"stress": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--seconds", type=int, default=15)
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument(
        "--paired",
        action="store_true",
        help="Four same-process runs: disabled/enabled/enabled/disabled",
    )
    parser.add_argument("--overlays", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.seconds <= 0:
        raise ValueError("Positive duration and new output path required")
    if args.config:
        shared = {}

        def interaction(config, geometry):
            shared["proxy"] = ProxyInteraction(config, geometry, evaluate=args.evaluate)
            return shared["proxy"]

        def run(enabled):
            return replay(
                args.config,
                args.seconds,
                corridor_factory=MeasuredCorridor,
                trajectory_factory=MeasuredTrajectory,
                interaction_factory=interaction,
                risk_factory=(lambda c: MeasuredRisk(c, shared["proxy"], args.evaluate))
                if enabled
                else None,
                renderer=DebugRisk(args.overlays) if args.overlays else None,
            )

        if args.paired:
            if args.evaluate or args.overlays:
                raise ValueError("Paired timing excludes evaluation and overlays")
            report = {
                "order": [False, True, True, False],
                "runs": [run(enabled) for enabled in (False, True, True, False)],
            }
        else:
            report = run(True)
    else:
        report = stress()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
