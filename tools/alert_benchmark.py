"""Local alert measurements; immutable historical attention replay is explicitly offline."""

import argparse
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from time import perf_counter_ns

from attention_benchmark import MeasuredAttention, fixture
from corridor_benchmark import MeasuredCorridor
from risk_benchmark import MeasuredRisk, ProxyInteraction
from trajectory_benchmark import MeasuredTrajectory
from world_benchmark import replay

from perception_lab.alerts import AlertEngine
from perception_lab.attention import NaiveAttentionPolicy
from perception_lab.attention_types import (
    AttentionAction,
    AttentionDecision,
    AttentionDecisionSet,
    AttentionEvent,
    SuppressedAttentionCandidate,
)
from perception_lab.contracts import ComponentProvenance
from perception_lab.metrics import Distribution
from perception_lab.risk_types import RiskLevel, RiskQuality, RiskTrend
from perception_lab.world_types import WorldEntityId


class MeasuredAlerts(AlertEngine):
    def __init__(self, config=None, timeline=None):
        super().__init__(config)
        self.timeline = timeline
        self.counts = Counter()
        self.source_age = Distribution(2048)
        self.attention_age = Distribution(2048)
        self.words = Counter()
        self.phrases = Counter()
        self.start = self.end = None

    def process(self, batch, **kwargs):
        result = super().process(batch, **kwargs)
        self.start = batch.state_timestamp if self.start is None else self.start
        self.end = batch.state_timestamp
        self.counts["updates"] += 1
        self.counts["selected_decisions_received"] += len(batch.selected)
        self.counts["interruption_decisions_received"] += sum(
            d.decision != AttentionAction.SILENT for d in batch.selected
        )
        self.counts["expired_in_attention"] += result.upstream_expired_candidates
        for output in result.outputs:
            self.counts[output.status] += 1
            self.counts["text_sink_accepted"] += output.delivered
            if output.presentation:
                self.counts["rendered"] += 1
                self.words[output.presentation.word_count] += 1
                self.phrases[output.presentation.speech_text] += 1
            if output.intent:
                if output.intent.source_observation_ns is not None:
                    self.source_age.add(kwargs["now_ns"] - output.intent.source_observation_ns)
                self.attention_age.add(kwargs["now_ns"] - output.intent.state_timestamp)
        if self.timeline:
            self.timeline.write(json.dumps(asdict(result)) + "\n")
        return result

    def report(self):
        span = (self.end - self.start) / 1e9 if self.start is not None else 0
        self.counts["intent_constructions"] = self.timings["intent"].count
        self.counts["still_valid_at_render"] = self.timings["render"].count
        self.counts["rendered_attempts"] = self.timings["render"].count
        return {
            "counts": dict(self.counts),
            "phrases": dict(self.phrases),
            "word_counts": dict(self.words),
            "compute": {k: v.summary() for k, v in self.timings.items()},
            "renderer_phases": {k: v.summary() for k, v in self.renderer.timings.items()},
            "source_to_alert_age": self.source_age.summary(),
            "attention_to_alert_age": self.attention_age.summary(),
            "source_span_seconds": span,
            "rates_per_source_minute": {
                k: v * 60 / span if span else None for k, v in self.counts.items()
            },
            "configuration": self.config.model_dump(),
            "delivery_scope": "Local text sink acceptance; no audible delivery or human validation",
        }


def decode_batch(row):
    if row.get("schema_version") != 1:
        raise ValueError("Unsupported attention schema")

    def decision(value):
        value = dict(value)
        value["entity_id"] = WorldEntityId(**value["entity_id"]) if value["entity_id"] else None
        value["event"] = AttentionEvent(**value["event"]) if value["event"] else None
        value["provenance"] = ComponentProvenance(**value["provenance"])
        value["decision"] = AttentionAction(value["decision"])
        value["source_risk_level"] = (
            RiskLevel(value["source_risk_level"]) if value["source_risk_level"] else None
        )
        value["source_risk_quality"] = (
            RiskQuality(value["source_risk_quality"]) if value["source_risk_quality"] else None
        )
        value["risk_trend"] = RiskTrend(value["risk_trend"])
        for key in ("reason_codes", "interaction_reasons"):
            value[key] = tuple(value[key])
        # Historical schema11 lacks original observation time. Keep it unknown.
        if value.get("semantic_evidence") is not None:
            raise ValueError("This historical replay reader accepts Task016 semantics only")
        return AttentionDecision(**value)

    return AttentionDecisionSet(
        row["session_id"],
        row["state_timestamp"],
        row["valid_until_ns"],
        tuple(decision(d) for d in row["selected"]),
        tuple(
            SuppressedAttentionCandidate(decision(s["decision"]), s["reason"])
            for s in row["suppressed"]
        ),
        row["scene_status"],
        tuple(row["reason_summaries"]),
        ComponentProvenance(**row["provenance"]),
        row["config_hash"],
        ComponentProvenance(**row["risk_provenance"]),
        row["upstream_coverage"],
    )


def offline(source, timeline):
    engine = MeasuredAlerts(timeline=timeline)
    with source.open(encoding="utf-8") as stream:
        for line in stream:
            batch = decode_batch(json.loads(line)["NOVELTY_ESCALATION"])
            engine.process(batch, now_ns=batch.state_timestamp, mode="OFFLINE_REPLAY_PRESENTATION")
    return {
        "mode": "OFFLINE_REPLAY_PRESENTATION",
        "source": source.name,
        "alerts": engine.report(),
        "scope": "Frozen Task016 decisions; offline only; original source age unavailable",
    }


def run(config, seconds, timeline=None, enabled=True):
    return replay(
        config,
        seconds,
        corridor_factory=MeasuredCorridor,
        trajectory_factory=MeasuredTrajectory,
        interaction_factory=lambda c, g: ProxyInteraction(c, g, evaluate=False),
        risk_factory=MeasuredRisk,
        attention_factory=lambda c: MeasuredAttention(c, compare=False),
        alert_factory=(lambda c: MeasuredAlerts(c, timeline)) if enabled else None,
    )


def stress():
    rows = []
    for count in (1, 10, 50, 100, 128, 512):
        engine = MeasuredAlerts()
        policy = NaiveAttentionPolicy()
        timer = Distribution(2048)
        for i in range(200):
            timestamp = i * 100_000_000
            batch = policy.decide(fixture(timestamp, count))
            started = perf_counter_ns()
            engine.process(batch, now_ns=timestamp)
            timer.add(perf_counter_ns() - started)
        rows.append(
            {
                "attention_candidates": count,
                "updates": 200,
                "total_instrumented": timer.summary(),
                "alerts": engine.report(),
            }
        )
    engines = [MeasuredAlerts(), MeasuredAlerts()]
    policy = NaiveAttentionPolicy()
    for i in range(72000):
        t = i * 100_000_000
        b = policy.decide(fixture(t))
        first, second = [e.process(b, now_ns=t) for e in engines]
        assert first == second and first.outputs[0].delivered
        assert all(
            len(e.presenter.history) <= 128 and len(e.presenter._ids) <= 128 for e in engines
        )
    return {
        "stress": rows,
        "soak": {
            "hours_equivalent": 2,
            "updates": 72000,
            "deterministic_two_runs": True,
            "bounded_history": 128,
            "pending_slots": 1,
            "unique_acceptances_per_run": engines[0].counts["text_sink_accepted"],
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path)
    parser.add_argument("--seconds", type=int, default=600)
    parser.add_argument("--attention-timeline", type=Path)
    parser.add_argument("--timeline", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stress", action="store_true")
    parser.add_argument("--paired", action="store_true")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise ValueError("Preserve prior results; select a new output")
    stream = args.timeline.open("x", encoding="utf-8") if args.timeline else None
    try:
        if args.stress:
            result = stress()
        elif args.attention_timeline:
            result = offline(args.attention_timeline, stream)
        elif args.paired:
            rows = [
                {"enabled": e, "result": run(args.config, args.seconds, enabled=e)}
                for e in (False, True, True, False)
            ]
            enabled = sum(r["result"]["wall_seconds"] for r in rows if r["enabled"])
            baseline = sum(r["result"]["wall_seconds"] for r in rows if not r["enabled"])
            result = {
                "runs": rows,
                "aggregate_overhead_percent": (enabled / baseline - 1) * 100,
                "scope": "Single local ABBA, no significance or hardware qualification",
            }
        else:
            result = run(args.config, args.seconds, stream)
        args.output.write_text(
            json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
    finally:
        if stream:
            stream.close()


if __name__ == "__main__":
    main()
