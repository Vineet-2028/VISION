"""Evaluation-only event accounting. References never inherit runtime validation."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

STAGES = (
    "DETECTION",
    "TRACK",
    "WORLD",
    "CORRIDOR",
    "TRAJECTORY",
    "INTERACTION",
    "RISK",
    "ATTENTION",
    "ALERT_INTENT",
    "VALID_ALERT",
    "DELIVERABLE_ALERT",
)
FAILURES = (
    "NOT_DETECTED",
    "DETECTED_NOT_TRACKED",
    "WORLD_ENTITY_MISSING",
    "CORRIDOR_RELATION_MISSING",
    "TRAJECTORY_UNAVAILABLE",
    "INTERACTION_NOT_DETECTED",
    "RISK_UNDETERMINED",
    "ATTENTION_SUPPRESSED",
    "ALERT_RENDER_FAILURE",
    "ALERT_EXPIRED",
    "ALERT_NOT_DELIVERABLE",
)
TAXONOMY = (
    "PERCEPTION_COVERAGE",
    "TRACKING_CONTINUITY",
    "DEPTH_SPATIAL",
    "EGO_MOTION",
    "WORLD_STATE",
    "CORRIDOR",
    "TRAJECTORY",
    "INTERACTION",
    "RISK",
    "ATTENTION",
    "ALERT",
    "FRESHNESS_LATENCY",
    "GROUND_TRUTH_LIMITATION",
    "UNKNOWN",
)


class LabelStatus(StrEnum):
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    PROXY = "PROXY"
    DRAFT = "DRAFT"
    AMBIGUOUS = "AMBIGUOUS"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class StageOutcome:
    stage: str
    status: Literal["PASS", "FAIL", "UNKNOWN"]
    first_observation_ns: int | None = None
    source_to_stage_age_ns: int | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.stage not in STAGES or self.status not in {"PASS", "FAIL", "UNKNOWN"}:
            raise ValueError("Invalid stage outcome")
        for value in (self.first_observation_ns, self.source_to_stage_age_ns):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("Invalid stage timestamp/age")


@dataclass(frozen=True)
class V0EventLedger:
    event_id: str
    source_session: str
    start_ns: int
    end_ns: int
    label_status: LabelStatus
    relevant: bool | None
    category: str
    interaction: str
    direction: str | None
    stages: tuple[StageOutcome, ...]
    first_failure_stage: str | None
    failure_reason: str | None
    first_stage_age_exceeded: str | None
    final_alert_state: str
    quadrant: str
    provenance: str
    notes: tuple[str, ...] = ()
    schema_version: int = 1

    def __post_init__(self) -> None:
        if not self.event_id or not self.source_session or not 0 <= self.start_ns <= self.end_ns:
            raise ValueError("Invalid event identity/interval")
        if tuple(s.stage for s in self.stages) != STAGES:
            raise ValueError("Every canonical stage must occur once in order")
        if (
            self.label_status
            in {LabelStatus.DRAFT, LabelStatus.AMBIGUOUS, LabelStatus.INSUFFICIENT_EVIDENCE}
            and self.relevant is not None
        ):
            raise ValueError("Unresolved review cannot establish relevance")
        if (self.first_failure_stage, self.failure_reason) != first_failure(self.stages):
            raise ValueError("First failure must agree with ordered stage evidence")
        if (
            self.first_stage_age_exceeded is not None
            and self.first_stage_age_exceeded not in STAGES
        ):
            raise ValueError("Unknown freshness stage")
        if not self.provenance:
            raise ValueError("Reference provenance required")


def first_failure(stages: tuple[StageOutcome, ...]) -> tuple[str | None, str | None]:
    """Unknown upstream evidence prevents asserting a later *first* failure."""
    for index, row in enumerate(stages):
        if row.status == "UNKNOWN":
            return row.stage, "GROUND_TRUTH_LIMITATION"
        if row.status == "FAIL":
            return row.stage, row.reason or FAILURES[index]
    return None, None


def quadrant(semantic_covered: bool | None, timely: bool | None) -> str:
    if semantic_covered is None or timely is None:
        return "UNKNOWN"
    return (
        ("A_CORRECT_TIMELY" if timely else "B_CORRECT_LATE")
        if semantic_covered
        else ("C_MISSED_TIMELY_PROCESSING" if timely else "D_MISSED_LATE")
    )


def summarize_events(rows: tuple[V0EventLedger, ...]) -> dict[str, object]:
    """Separate reference strata and event denominators; never sum downstream misses."""
    keys = [(r.source_session, r.event_id) for r in rows]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate source event")
    groups: dict[str, object] = {}
    for status in LabelStatus:
        group = [r for r in rows if r.label_status == status]
        relevant = [r for r in group if r.relevant is True]
        headline = status in {LabelStatus.HUMAN_REVIEWED, LabelStatus.PROXY}
        failures: dict[str, int] = {}
        for row in relevant:
            if row.first_failure_stage is not None:
                failures[row.first_failure_stage] = failures.get(row.first_failure_stage, 0) + 1
        conditional = []
        for index, name in enumerate(STAGES):
            eligible = [r for r in relevant if all(s.status == "PASS" for s in r.stages[:index])]
            hits = sum(r.stages[index].status == "PASS" for r in eligible)
            conditional.append(
                {
                    "stage": name,
                    "numerator": hits,
                    "denominator": len(eligible),
                    "coverage": hits / len(eligible) if eligible and headline else None,
                }
            )
        end_hits = sum(all(s.status == "PASS" for s in r.stages) for r in relevant)
        groups[status.value] = {
            "events": len(group),
            "relevant_events": len(relevant) if headline else None,
            "conditional_stage_coverage": conditional,
            "end_to_end": {
                "numerator": end_hits if headline else None,
                "denominator": len(relevant) if headline else None,
                "coverage": end_hits / len(relevant) if relevant and headline else None,
            },
            "first_failure_counts": failures,
            "first_failure_percent": {k: v * 100 / len(relevant) for k, v in failures.items()},
        }
    return groups
