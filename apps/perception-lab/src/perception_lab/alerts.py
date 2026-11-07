"""Attention-only deterministic presentation stage. No geometry or inference."""

import hashlib
from collections.abc import Callable
from time import perf_counter_ns
from typing import cast

from .alert_config import AlertConfig
from .alert_presenter import NullAlertPresenter, RecordingAlertPresenter
from .alert_renderer import CATEGORIES, DIRECTIONS, EnglishV1AlertRenderer, bounded_concept_text
from .alert_types import (
    AlertIntent,
    AlertOutput,
    AlertOutputSet,
    AlertPresenter,
    AlertRenderer,
    Category,
    Direction,
    Interaction,
)
from .attention_types import AttentionAction, AttentionDecision, AttentionDecisionSet
from .contracts import ComponentProvenance
from .metrics import Distribution

INTERACTIONS = {"CROSSING", "APPROACHING", "IN_CORRIDOR", "STATIC_OBSTACLE", "GENERIC"}
CATEGORY_ALIASES = {"CAR": "VEHICLE", "BUS": "VEHICLE", "TRUCK": "VEHICLE"}


class AlertEngine:
    def __init__(
        self,
        config: AlertConfig | None = None,
        *,
        renderer: AlertRenderer | None = None,
        presenter: AlertPresenter | None = None,
    ) -> None:
        self.config = config or AlertConfig()
        self.config_hash = hashlib.sha256(self.config.model_dump_json().encode()).hexdigest()
        self.provenance = ComponentProvenance(
            "alerts-v1", "alerts", configuration_hash=self.config_hash
        )
        self.renderer = renderer or EnglishV1AlertRenderer(self.config)
        self.presenter = presenter or (
            NullAlertPresenter(self.config.history_size)
            if self.config.sink_mode == "NULL"
            else RecordingAlertPresenter(self.config.history_size)
        )
        self.timings = {
            name: Distribution(2048) for name in ("intent", "render", "present", "total")
        }
        self.reset()

    def reset(self, session_id: str | None = None) -> None:
        self.session_id = session_id
        self._timestamp = -1
        self._now = -1
        self.presenter.reset(session_id)

    def _intent(self, d: AttentionDecision, batch: AttentionDecisionSet) -> AlertIntent:
        assert d.event is not None
        category, direction, interaction = "UNKNOWN", "UNKNOWN", "GENERIC"
        concept_text = None
        evidence = d.semantic_evidence
        reasons = (*d.reason_codes, "PROTOTYPE_LANGUAGE_UNVALIDATED")
        sources: tuple[ComponentProvenance, ...] = (
            batch.risk_provenance,
            d.provenance,
            self.provenance,
        )
        if (
            evidence is not None
            and evidence.entity_id == d.entity_id
            and evidence.entity_id.session_id == batch.session_id
            and 0 <= evidence.observed_ns <= d.state_timestamp < evidence.valid_until_ns
            and evidence.quality in {"GOOD", "DEGRADED"}
            and evidence.provenance
        ):
            category = CATEGORY_ALIASES.get(evidence.category or "", evidence.category or "UNKNOWN")
            category = category if category in CATEGORIES else "UNKNOWN"
            direction = evidence.direction if evidence.direction in DIRECTIONS else "UNKNOWN"
            interaction = (
                evidence.interaction if evidence.interaction in INTERACTIONS else "GENERIC"
            )
            sources += evidence.provenance
            if evidence.quality == "GOOD" and evidence.concept is not None:
                concept_text = bounded_concept_text(evidence.concept.normalized_label)
            elif evidence.quality == "GOOD" and evidence.group_spoken_label is not None:
                concept_text = bounded_concept_text(evidence.group_spoken_label)
        else:
            reasons += ("SEMANTICS_UNAVAILABLE",)
        deadline = min(
            batch.valid_until_ns, d.event.valid_until_ns, d.state_timestamp + self.config.max_age_ns
        )
        if evidence is not None and (
            category != "UNKNOWN"
            or direction != "UNKNOWN"
            or interaction != "GENERIC"
            or concept_text is not None
        ):
            deadline = min(deadline, evidence.valid_until_ns)
        if d.source_observation_ns is not None:
            deadline = min(deadline, d.source_observation_ns + self.config.max_age_ns)
        return AlertIntent(
            f"{batch.session_id}:{d.event.event_id}:alert-v1",
            d.event.event_id,
            d.event.episode_id,
            batch.session_id,
            d.state_timestamp,
            d.source_observation_ns,
            d.entity_id,
            d.decision,
            cast(Category, category),
            cast(Direction, direction),
            cast(Interaction, interaction),
            d.priority,
            d.source_risk_level,
            d.quality,
            d.physical_validity,
            deadline,
            reasons,
            sources,
            self.config_hash,
            d.source_age_basis,
            concept_text=concept_text,
            lineage=d.lineage,
            semantic_level=(
                "SPECIFIC"
                if concept_text is not None
                and evidence is not None
                and evidence.concept is not None
                else "GROUP"
                if concept_text is not None
                else "GENERIC"
            ),
        )

    def process(
        self,
        batch: AttentionDecisionSet,
        *,
        now_ns: int,
        mode: str = "REALTIME",
        delivery_clock: Callable[[], int] | None = None,
    ) -> AlertOutputSet:
        started = perf_counter_ns()
        expired = 0

        def finish(outputs: tuple[AlertOutput, ...]) -> AlertOutputSet:
            self.timings["total"].add(perf_counter_ns() - started)
            return AlertOutputSet(batch.session_id, now_ns, mode, outputs, expired, self.provenance)

        if (
            batch.schema_version != 1
            or batch.state_timestamp < 0
            or not batch.session_id
            or (self.session_id is not None and batch.session_id != self.session_id)
            or now_ns < batch.state_timestamp
            or now_ns < self._now
            or batch.state_timestamp < self._timestamp
            or len(batch.selected) > 1
            or len(batch.suppressed) > 512
            or mode not in {"REALTIME", "OFFLINE_REPLAY_PRESENTATION"}
        ):
            return finish((AlertOutput("DROPPED_INVALID", "SESSION_CLOCK_SCHEMA_OR_BOUNDS"),))
        if self.session_id is None:
            self.reset(batch.session_id)
        expired = sum(s.reason == "EVENT_EXPIRED" for s in batch.suppressed)
        self._timestamp, self._now = batch.state_timestamp, now_ns
        outputs = []
        for d in batch.selected:
            if d.decision == AttentionAction.SILENT:
                outputs.append(AlertOutput("NO_PRESENTATION", "ATTENTION_SILENT"))
                continue
            if (
                d.event is None
                or d.decision
                not in {AttentionAction.ANNOUNCE, AttentionAction.REPEAT, AttentionAction.ESCALATE}
                or d.state_timestamp != batch.state_timestamp
                or d.priority not in range(5)
                or (d.entity_id is not None and d.entity_id.session_id != batch.session_id)
                or (
                    d.source_observation_ns is not None
                    and not 0 <= d.source_observation_ns <= d.state_timestamp
                )
                or not d.event.event_id
                or not d.event.episode_id
                or d.event.created_ns > d.state_timestamp
                or d.event.created_ns < 0
            ):
                outputs.append(AlertOutput("DROPPED_INVALID", "INVALID_ATTENTION_DECISION"))
                continue
            tick = perf_counter_ns()
            intent = self._intent(d, batch)
            self.timings["intent"].add(perf_counter_ns() - tick)
            if now_ns >= intent.valid_until_ns:
                outputs.append(AlertOutput("DROPPED_EXPIRED", "EXPIRED_BEFORE_RENDER", intent))
                continue
            tick = perf_counter_ns()
            try:
                presentation = self.renderer.render(intent, now_ns)
            except (ValueError, KeyError):
                outputs.append(AlertOutput("UNRENDERABLE", "RENDERER_REJECTED", intent))
                continue
            self.timings["render"].add(perf_counter_ns() - tick)
            tick = perf_counter_ns()
            delivery_now = delivery_clock() if delivery_clock else now_ns
            outputs.append(self.presenter.submit(intent, presentation, delivery_now))
            self.timings["present"].add(perf_counter_ns() - tick)
        return finish(tuple(outputs))
