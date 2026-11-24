"""Task016 local causal policy comparisons; no reviewed hazard/usefulness truth."""

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from time import perf_counter_ns

from corridor_benchmark import MeasuredCorridor
from risk_benchmark import MeasuredRisk, ProxyInteraction
from trajectory_benchmark import MeasuredTrajectory
from world_benchmark import replay

from perception_lab.attention import NoveltyEscalationAttentionPolicy
from perception_lab.attention_config import AttentionConfig
from perception_lab.attention_types import AttentionAction
from perception_lab.contracts import ComponentProvenance, Frame
from perception_lab.metrics import Distribution
from perception_lab.risk_types import (
    RiskAssessment,
    RiskAssessmentSet,
    RiskLevel,
    RiskQuality,
    RiskTrend,
)
from perception_lab.world_types import WorldEntityId

POLICIES = ("NAIVE", "COOLDOWN", "NOVELTY_ESCALATION")


def fixture(timestamp=0, count=1, level=RiskLevel.HIGH, first_id=0):
    provenance = ComponentProvenance("synthetic-risk", "risk")
    rows = tuple(
        RiskAssessment(
            WorldEntityId("synthetic", first_id + i),
            timestamp,
            timestamp + 500_000_000,
            level,
            RiskQuality.DEGRADED,
            (),
            (),
            ("CURRENT_OCCUPANCY",),
            None,
            (),
            ("CURRENT_OCCUPANCY",),
            RiskTrend.STABLE,
            (provenance,),
            "fixture",
            "UNVERIFIED",
        )
        for i in range(count)
    )
    return RiskAssessmentSet(
        "synthetic",
        timestamp,
        timestamp + 500_000_000,
        rows,
        (),
        (),
        (),
        (),
        provenance,
        "fixture",
        provenance,
    )


class AttentionProxy(ProxyInteraction):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attention_events = {p: Counter() for p in POLICIES}
        self.attention_funnel = {p: Counter() for p in POLICIES}
        self.leads = {p: Distribution(2048) for p in POLICIES}
        self.lateness = {p: Distribution(2048) for p in POLICIES}

    def on_evaluated(self, item, predicted, actual):
        super().on_evaluated(item, predicted, actual)
        for policy in POLICIES:
            emitted = item.get("attention", {}).get(policy, False)
            self.attention_events[policy][
                "TP" if emitted and actual else "FP" if emitted else "FN" if actual else "TN"
            ] += 1
            counts = self.attention_funnel[policy]
            counts["eligible_proxy_windows"] += 1
            counts["proxy_relevant"] += actual
            counts["attention_at_frozen_start"] += emitted
            counts["attention_and_relevant"] += emitted and actual
            counts["interaction_and_risk_and_attention"] += (
                actual and predicted and emitted and item.get("risk") in {"HIGH", "ELEVATED"}
            )
            first = item.get("first_attention", {}).get(policy)
            if predicted and actual and first is not None:
                lead = item["start"] + item["entry"] - first
                if lead >= 0:
                    self.leads[policy].add(lead)
                else:
                    self.lateness[policy].add(-lead)

    def report(self):
        return {
            **super().report(),
            "attention_proxy": {
                p: {
                    "events": dict(self.attention_events[p]),
                    "funnel": dict(self.attention_funnel[p]),
                    "first_attention_lead_proxy": self.leads[p].summary(),
                    "late_attention_delay_proxy": self.lateness[p].summary(),
                }
                for p in POLICIES
            },
        }


class MeasuredAttention(NoveltyEscalationAttentionPolicy):
    def __init__(self, config, proxy=None, timeline=None, compare=True):
        super().__init__(config)
        self.variants = (
            {p: NoveltyEscalationAttentionPolicy(AttentionConfig(policy=p)) for p in POLICIES}
            if compare
            else {}
        )
        self.proxy, self.timeline = proxy, timeline
        self.timer = Distribution(4096)
        self.serialization = Distribution(128)
        self.counts = {p: Counter() for p in POLICIES}
        self.reasons = {p: Counter() for p in POLICIES}
        self.episodes = {p: set() for p in POLICIES}
        self.covered = {p: set() for p in POLICIES}
        self.last_interrupt = {p: None for p in POLICIES}
        self.intervals = {p: Distribution(2048) for p in POLICIES}
        self.start = self.end = None
        self.peak_history = self.peak_scene_history = 0

    def decide(self, risk, audio=None, *, now_ns=None):
        start = perf_counter_ns()
        result = super().decide(risk, audio, now_ns=now_ns)
        self.timer.add(perf_counter_ns() - start)
        self.peak_history = max(self.peak_history, self.history_size)
        self.peak_scene_history = max(self.peak_scene_history, self.scene_history_size)
        self.start = risk.state_timestamp if self.start is None else self.start
        self.end = risk.state_timestamp
        outputs = {
            p: engine.decide(risk, audio, now_ns=now_ns) for p, engine in self.variants.items()
        }
        if not outputs:
            outputs = {"NOVELTY_ESCALATION": result}
        for p, output in outputs.items():
            counts = self.counts[p]
            counts["updates"] += 1
            chosen = [d for d in output.selected if d.decision != AttentionAction.SILENT]
            counts["silent_updates"] += not chosen
            counts["suppressed"] += len(output.suppressed)
            counts["candidate_updates"] += len(risk.assessments)
            self.reasons[p].update(s.reason for s in output.suppressed)
            all_decisions = (*output.selected, *(s.decision for s in output.suppressed))
            for d in all_decisions:
                if d.event is not None:
                    self.episodes[p].add(d.event.episode_id)
            for d in chosen:
                counts[d.decision.value] += 1
                self.covered[p].add(d.event.episode_id)
                if self.last_interrupt[p] is not None:
                    self.intervals[p].add(risk.state_timestamp - self.last_interrupt[p])
                self.last_interrupt[p] = risk.state_timestamp
                counts["selected_with_current_occupancy"] += (
                    "CURRENTLY_INSIDE_CORRIDOR" in d.interaction_reasons
                )
            if self.proxy is not None:
                ids = {d.entity_id for d in chosen}
                for item in self.proxy.pending:
                    if item["start"] == risk.state_timestamp:
                        item.setdefault("attention", {})[p] = item["entity"] in ids
                    if item["entity"] in ids:
                        item.setdefault("first_attention", {}).setdefault(p, risk.state_timestamp)
        if self.timeline is not None:
            start = perf_counter_ns()
            self.timeline.write(json.dumps({p: asdict(o) for p, o in outputs.items()}) + "\n")
            self.serialization.add(perf_counter_ns() - start)
        return result

    def report(self):
        seconds = (
            ((self.end - self.start) / 1e9)
            if self.start is not None and self.end is not None
            else 0
        )
        return {
            "compute": self.timer.summary(),
            "recording": self.serialization.summary(),
            "peak_history": self.peak_history,
            "peak_scene_history": self.peak_scene_history,
            "configuration": self.config.model_dump(),
            "config_hash": self.config_hash,
            "source_span_seconds": seconds,
            "policies": {
                p: {
                    "counts": dict(c),
                    "suppression_reasons": dict(self.reasons[p]),
                    "unique_qualifying_episodes": len(self.episodes[p]),
                    "covered_episodes": len(self.covered[p]),
                    "conditional_episode_coverage": len(self.covered[p]) / len(self.episodes[p])
                    if self.episodes[p]
                    else None,
                    "per_minute": {
                        k: c[k] * 60 / seconds if seconds else None
                        for k in ("ANNOUNCE", "REPEAT", "ESCALATE", "suppressed")
                    },
                    "silent_update_ratio": c["silent_updates"] / c["updates"]
                    if c["updates"]
                    else None,
                    "suppressed_candidate_ratio": c["suppressed"] / c["candidate_updates"]
                    if c["candidate_updates"]
                    else None,
                    "interruption_intervals": self.intervals[p].summary(),
                }
                for p, c in self.counts.items()
            },
            "human_validated": False,
            "scope": "CONDITIONAL RISK-EPISODE COVERAGE; NOT HAZARD RECALL",
        }


class WindowSource:
    """Benchmark-only 5Hz sampling within all draft windows; no timestamp rewriting."""

    def __init__(self, source, windows):
        self.source, self.windows = source, windows

    def __iter__(self):
        next_ns = -1
        index = 0
        for frame in self.source:
            if not isinstance(frame, Frame):
                yield frame
                continue
            ns = frame.identity.observation_ns
            while index < len(self.windows) and ns >= self.windows[index]["end_seconds"] * 1e9:
                index += 1
            if index == len(self.windows):
                break
            if ns >= self.windows[index]["start_seconds"] * 1e9 and ns >= next_ns:
                next_ns = ns + 200_000_000
                yield frame

    def close(self):
        self.source.close()


def run(config, seconds, timeline=None, windows=None, compare=True, evaluate=True):
    proxy = None

    def interaction(c, g):
        nonlocal proxy
        proxy = AttentionProxy(c, g, evaluate=evaluate and windows is None and seconds <= 30)
        return proxy

    return replay(
        config,
        seconds,
        corridor_factory=MeasuredCorridor,
        trajectory_factory=MeasuredTrajectory,
        interaction_factory=interaction,
        risk_factory=lambda c: MeasuredRisk(c, proxy),
        attention_factory=lambda c: MeasuredAttention(c, proxy, timeline, compare),
        source_transform=(lambda s: WindowSource(s, windows)) if windows else None,
    )


def stress():
    rows = []
    for count in (1, 10, 50, 100, 128, 512):
        engine = NoveltyEscalationAttentionPolicy()
        timer = Distribution(2048)
        for i in range(200):
            value = fixture(i * 100_000_000, count)
            start = perf_counter_ns()
            output = engine.decide(value)
            timer.add(perf_counter_ns() - start)
            assert len(output.selected) == 1 and engine.history_size <= count
        rows.append(
            {
                "entities": count,
                "timing": timer.summary(),
                "history": engine.history_size,
            }
        )
    engines = [NoveltyEscalationAttentionPolicy() for _ in range(2)]
    actions = Counter()
    for i in range(72_000):  # Two observation-hours at 10Hz, accelerated without sleeping.
        value = fixture(i * 100_000_000, count=3, first_id=(i // 100) * 3)
        a, b = [e.decide(value) for e in engines]
        assert a == b
        assert all(e.history_size <= 512 and e.scene_history_size <= 10 for e in engines)
        actions.update(d.decision.value for d in a.selected)
    scenarios = {}
    for name, count, levels in (
        ("crowd", 50, [RiskLevel.ELEVATED] * 600),
        ("oscillation", 1, [RiskLevel.ELEVATED, RiskLevel.HIGH] * 300),
        ("persistent", 1, [RiskLevel.HIGH] * 600),
    ):
        measured = MeasuredAttention(AttentionConfig())
        for i, level in enumerate(levels):
            measured.decide(fixture(i * 100_000_000, count, level))
        scenarios[name] = measured.report()
    return {
        "stress": rows,
        "long_synthetic": {
            "hours": 2,
            "updates": 72000,
            "actions": dict(actions),
            "final_history": engines[0].history_size,
            "deterministic_two_runs": True,
        },
        "scenarios": scenarios,
        "instrumented_phases": profile_phases(),
    }


def profile_phases():
    """Line profiler outside the policy; timings include tracing overhead."""
    import inspect

    source, offset = inspect.getsourcelines(NoveltyEscalationAttentionPolicy.decide)
    boundaries = {
        "history": next(i + offset for i, s in enumerate(source) if "self._episodes = {" in s),
        "candidates": next(i + offset for i, s in enumerate(source) if "for a in sorted" in s),
        "ranking": next(i + offset for i, s in enumerate(source) if "candidates.sort(" in s),
        "selection": next(i + offset for i, s in enumerate(source) if "selected: list" in s),
        "output": next(
            i + offset for i, s in enumerate(source) if "return AttentionDecisionSet(" in s
        ),
    }
    filename = inspect.getfile(NoveltyEscalationAttentionPolicy)
    totals = Counter()
    previous = [None, 0]

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != filename:
            return None
        if event in {"line", "return"}:
            now = perf_counter_ns()
            if previous[0] is not None:
                totals[previous[0]] += now - previous[1]
            phase = "validation"
            if frame.f_code.co_name == "_decision":
                phase = "decision_construction"
            elif frame.f_code.co_name == "_gate":
                phase = "quality_gates"
            elif frame.f_code.co_name == "decide":
                for name, line in boundaries.items():
                    if frame.f_lineno >= line:
                        phase = name
            previous[:] = [phase, now]
        return tracer

    engine = NoveltyEscalationAttentionPolicy()
    try:
        for i in range(30):
            value = fixture(i * 100_000_000, 50)
            previous[0] = None
            sys.settrace(tracer)
            engine.decide(value)
            sys.settrace(None)
    finally:
        sys.settrace(None)
    return {
        "mean_ns_per_50_entity_update": {k: v / 30 for k, v in totals.items()},
        "scope": "Instrumented phase attribution includes tracing overhead; not runtime latency",
    }


def paired(config, seconds):
    """Same-process ABBA, identical source/config and no policy comparison recording."""
    rows = []
    for enabled in (False, True, True, False):
        if enabled:
            result = run(config, seconds, compare=False, evaluate=False)
        else:
            result = replay(
                config,
                seconds,
                corridor_factory=MeasuredCorridor,
                trajectory_factory=MeasuredTrajectory,
                interaction_factory=ProxyInteraction,
                risk_factory=MeasuredRisk,
            )
        rows.append({"attention_enabled": enabled, "result": result})
    baseline = sum(r["result"]["wall_seconds"] for r in rows if not r["attention_enabled"])
    enabled = sum(r["result"]["wall_seconds"] for r in rows if r["attention_enabled"])
    return {
        "runs": rows,
        "aggregate_overhead_percent": (enabled / baseline - 1) * 100,
        "provisional_overhead_gate_percent": 5,
        "scope": "Single local ABBA control; no statistical or target-device guarantee",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path)
    parser.add_argument("--seconds", type=int, default=15)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeline", type=Path)
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--stress", action="store_true")
    parser.add_argument("--primary-only", action="store_true")
    parser.add_argument("--paired", action="store_true")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.stress:
        result = stress()
    elif args.paired:
        result = paired(args.config, args.seconds)
    else:
        packet = json.loads(args.packet.read_text()) if args.packet else None
        stream = args.timeline.open("x", encoding="utf-8") if args.timeline else None
        try:
            result = run(
                args.config,
                args.seconds,
                stream,
                packet["windows"] if packet else None,
                not args.primary_only,
            )
            if packet:
                if result["source_sha256"] != packet["source_sha256"]:
                    raise ValueError("Review source hash mismatch")
                result["packet_sampling"] = "All 30 draft windows at 5Hz, context gaps preserved"
        finally:
            if stream:
                stream.close()
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
