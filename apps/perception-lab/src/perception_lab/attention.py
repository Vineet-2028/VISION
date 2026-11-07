"""Deterministic bounded policy over risk contracts. Single pipeline-thread owner."""

import hashlib
from collections import deque
from dataclasses import dataclass, replace

from .attention_config import AttentionConfig
from .attention_types import (
    AttentionAction,
    AttentionDecision,
    AttentionDecisionSet,
    AttentionEvent,
    AudioChannelState,
    SuppressedAttentionCandidate,
)
from .contracts import ComponentProvenance
from .risk_types import RiskAssessment, RiskAssessmentSet, RiskLevel, RiskQuality, RiskTrend
from .world_types import WorldEntityId

LEVEL = {
    RiskLevel.UNDETERMINED: 0,
    RiskLevel.LOW: 1,
    RiskLevel.ELEVATED: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.SEVERE: 4,
}


@dataclass
class AttentionEpisode:
    episode_id: str
    started: int
    last_seen: int
    last_level: int = 0
    announced_level: int = 0
    last_announcement: int | None = None
    repeat_count: int = 0
    active: bool = True
    continuous_since: int = 0
    event: AttentionEvent | None = None
    signature: tuple[str, ...] = ()


class NoveltyEscalationAttentionPolicy:
    """No queued output: busy candidates are reconsidered only with fresh input.

    A bounded episode ledger retains delivery intent, never claims audio was played.
    Escalation can bypass ordinary cooldown/rate limits only above the highest
    priority already emitted in the rate window. Absolute output bound is therefore
    max_interruptions + four ordinal increases per window.
    """

    def __init__(self, config: AttentionConfig | None = None) -> None:
        config = config or AttentionConfig()
        self.config = config
        self.config_hash = hashlib.sha256(config.model_dump_json().encode()).hexdigest()
        self.provenance = ComponentProvenance(
            "attention-" + config.policy.lower(), "attention", configuration_hash=self.config_hash
        )
        self.reset()

    def reset(self) -> None:
        self._session: str | None = None
        self._timestamp = -1
        self._now = -1
        self._episodes: dict[WorldEntityId, AttentionEpisode] = {}
        self._recent: deque[tuple[int, int]] = deque(maxlen=self.config.max_interruptions + 4)

    @property
    def history_size(self) -> int:
        return len(self._episodes)

    @property
    def scene_history_size(self) -> int:
        return len(self._recent)

    def _decision(
        self,
        now: int,
        assessment: RiskAssessment | None,
        reason: str,
        episode: AttentionEpisode | None = None,
    ) -> AttentionDecision:
        return AttentionDecision(
            now,
            assessment.entity_id if assessment else None,
            AttentionAction.SILENT,
            LEVEL[assessment.risk_level] if assessment else 0,
            assessment.risk_level if assessment else None,
            assessment.evidence_quality if assessment else None,
            assessment.trend if assessment else RiskTrend.UNKNOWN,
            (reason,),
            "KNOWN",
            False,
            episode.repeat_count if episode else 0,
            False,
            "UNAVAILABLE",
            None,
            assessment.reason_codes if assessment else (),
            self.provenance,
            self.config_hash,
            source_observation_ns=(
                max(
                    0,
                    assessment.state_timestamp
                    - max(
                        (age for _, age in assessment.source_ages if age is not None and age >= 0),
                        default=0,
                    ),
                )
                if assessment
                else None
            ),
            source_age_basis=(
                "OLDEST_REPORTED_EVIDENCE"
                if assessment and any(age is not None for _, age in assessment.source_ages)
                else "RISK_STATE_ONLY"
                if assessment
                else "UNAVAILABLE"
            ),
            physical_validity=str(assessment.physical_validity or "UNVALIDATED")
            if assessment
            else "UNVALIDATED",
        )

    def decide(
        self,
        risk: RiskAssessmentSet,
        audio: AudioChannelState | None = None,
        *,
        now_ns: int | None = None,
    ) -> AttentionDecisionSet:
        audio = audio or AudioChannelState()
        now = risk.state_timestamp if now_ns is None else now_ns
        ids = {a.entity_id for a in risk.assessments}
        if (
            risk.schema_version != 1
            or risk.state_timestamp < 0
            or now < risk.state_timestamp
            or len(risk.assessments) > self.config.max_entities
            or len(ids) != len(risk.assessments)
            or any(i.session_id != risk.session_id for i in ids)
            or audio.active_priority not in range(5)
        ):
            raise ValueError("Invalid attention input schema, time, identity or bounds")
        if any(a.state_timestamp != risk.state_timestamp for a in risk.assessments):
            raise ValueError("Mismatched risk assessment timestamp")
        if self._session != risk.session_id:
            self.reset()
            self._session = risk.session_id
        if risk.state_timestamp < self._timestamp or now < self._now:
            raise ValueError("Attention clock moved backwards; reset explicitly on replay seek")
        duplicate = risk.state_timestamp == self._timestamp
        self._timestamp, self._now = risk.state_timestamp, now
        self._episodes = {
            i: e
            for i, e in self._episodes.items()
            if now - e.last_seen <= self.config.history_retention_ns
        }
        retained = sorted(
            self._episodes, key=lambda i: (i not in ids, -self._episodes[i].last_seen, i)
        )
        slots = self.config.max_entities - len(ids - self._episodes.keys())
        self._episodes = {i: self._episodes[i] for i in retained[:slots]}
        for i, e in self._episodes.items():
            if i not in ids:
                e.active = False
        while self._recent and now - self._recent[0][0] >= self.config.rate_window_ns:
            self._recent.popleft()
        suppressed: list[SuppressedAttentionCandidate] = []
        candidates: list[AttentionDecision] = []
        for a in sorted(risk.assessments, key=lambda a: a.entity_id):
            reason = self._gate(a, risk, now)
            if duplicate:
                reason = "DUPLICATE_STATE"
            if reason:
                if not duplicate and a.entity_id in self._episodes:
                    self._episodes[a.entity_id].active = False
                suppressed.append(
                    SuppressedAttentionCandidate(self._decision(now, a, reason), reason)
                )
                continue
            prior = self._episodes.get(a.entity_id)
            new = prior is None
            reappeared = prior is not None and (
                now - prior.last_seen >= self.config.reappearance_ns
            )
            if new or reappeared:
                prior = AttentionEpisode(
                    f"{a.entity_id.session_id}:{a.entity_id.serial}:{now}", now, now
                )
                self._episodes[a.entity_id] = prior
            assert prior is not None
            level = LEVEL[a.risk_level]
            novelty = (
                "REAPPEARED"
                if reappeared
                else "NEW"
                if new
                else (
                    "ESCALATED"
                    if level > prior.last_level
                    else "DEESCALATED"
                    if level < prior.last_level
                    else "KNOWN"
                )
            )
            if novelty == "KNOWN" and a.reason_codes != prior.signature:
                novelty = "CHANGED"
            prior.signature = a.reason_codes
            if new or reappeared or not prior.active:
                prior.continuous_since = now
            prior.last_seen, prior.last_level, prior.active = now, level, True
            cooldown = (
                prior.last_announcement is not None
                and now - prior.last_announcement < self.config.cooldown_ns
            )
            escalation = prior.announced_level > 0 and level > prior.announced_level
            elapsed = now - prior.last_announcement if prior.last_announcement is not None else 0
            action, reason = AttentionAction.SILENT, "REPEAT_SUPPRESSED"
            if prior.last_announcement is None:
                action, reason = AttentionAction.ANNOUNCE, "NEW_RELEVANT_ENTITY"
            elif escalation and self.config.escalation_override:
                action, reason = AttentionAction.ESCALATE, "RISK_ESCALATED"
            elif self.config.policy == "NAIVE":
                action, reason = AttentionAction.REPEAT, "NAIVE_QUALIFYING_UPDATE"
            elif not cooldown and (
                self.config.policy == "COOLDOWN"
                or (
                    elapsed >= self.config.repeat_interval_ns
                    and now - prior.continuous_since >= self.config.repeat_interval_ns
                    and level >= 3
                    and novelty != "DEESCALATED"
                )
            ):
                action, reason = AttentionAction.REPEAT, "RISK_PERSISTED"
            elif cooldown:
                reason = "COOLDOWN_ACTIVE"
            event = prior.event
            if action != AttentionAction.SILENT:
                event_id = f"{prior.episode_id}:{action.value}:{level}:{prior.repeat_count}"
                created = event.created_ns if event and event.event_id == event_id else now
                event = AttentionEvent(
                    event_id,
                    prior.episode_id,
                    reason,
                    created,
                    min(
                        risk.valid_until_ns,
                        a.valid_until_ns,
                        risk.state_timestamp + self.config.event_validity_ns,
                    ),
                )
                prior.event = event
            decision = replace(
                self._decision(now, a, reason, prior),
                decision=action,
                novelty=novelty,
                cooldown_active=cooldown,
                escalation=action == AttentionAction.ESCALATE,
                quality="DEGRADED",
                event=event,
            )
            if action == AttentionAction.SILENT:
                suppressed.append(SuppressedAttentionCandidate(decision, reason))
            else:
                candidates.append(decision)
        # Stronger > escalation > first intent > repeat > ascending stable identity.
        candidates.sort(
            key=lambda d: (
                -d.priority,
                -int(d.escalation),
                d.decision == AttentionAction.REPEAT,
                d.entity_id,
            )
        )
        selected: list[AttentionDecision] = []
        for d in candidates:
            reason = None
            maximum = max(
                max((p for _, p in self._recent), default=0),
                audio.active_priority if audio.busy else 0,
            )
            override = self.config.escalation_override and d.priority > maximum and maximum > 0
            if selected:
                reason = "PREEMPTED_BY_HIGHER_PRIORITY"
            elif audio.busy and not (override and d.priority > audio.active_priority):
                reason = "AUDIO_BUSY"
            elif (
                self.config.policy != "NAIVE"
                and not override
                and self._recent
                and (
                    len(self._recent) >= self.config.max_interruptions
                    or now - self._recent[-1][0] < self.config.global_interval_ns
                )
            ):
                reason = "GLOBAL_RATE_LIMIT"
            if reason:
                suppressed.append(
                    SuppressedAttentionCandidate(
                        replace(d, decision=AttentionAction.SILENT, reason_codes=(reason,)), reason
                    )
                )
            else:
                assert d.entity_id is not None
                episode = self._episodes[d.entity_id]
                episode.last_announcement = now
                episode.announced_level = max(episode.announced_level, d.priority)
                episode.repeat_count += int(d.decision == AttentionAction.REPEAT)
                self._recent.append((now, d.priority))
                if override:
                    d = replace(d, reason_codes=(*d.reason_codes, "HIGHER_PRIORITY_OVERRIDE"))
                if audio.busy:
                    d = replace(d, reason_codes=(*d.reason_codes, "PREEMPT_AUDIO_INTENT"))
                selected.append(d)
        if not selected:
            selected.append(self._decision(now, None, "NO_INTERRUPT_NOT_A_SAFETY_VERDICT"))
        return AttentionDecisionSet(
            risk.session_id,
            now,
            min(risk.valid_until_ns, risk.state_timestamp + self.config.event_validity_ns),
            tuple(selected),
            tuple(suppressed),
            "SILENT" if selected[0].decision == AttentionAction.SILENT else "INTERRUPTION_INTENT",
            tuple(sorted({s.reason for s in suppressed})),
            self.provenance,
            self.config_hash,
            risk.provenance,
            risk.upstream_coverage,
        )

    def _gate(self, a: RiskAssessment, risk: RiskAssessmentSet, now: int) -> str | None:
        if now >= min(
            a.valid_until_ns, risk.valid_until_ns, a.state_timestamp + self.config.event_validity_ns
        ):
            return "EVENT_EXPIRED"
        if a.risk_level == RiskLevel.UNDETERMINED:
            return "UNDETERMINED_RISK"
        if a.evidence_quality == RiskQuality.INSUFFICIENT or (
            a.evidence_quality == RiskQuality.DEGRADED and not self.config.allow_degraded
        ):
            return "LOW_EVIDENCE_QUALITY"
        minimum = 3 if self.config.mode == "CONSERVATIVE_ATTENTION" else 2
        if LEVEL[a.risk_level] < minimum:
            return "ENTITY_RESOLVED"
        return None


class NaiveAttentionPolicy(NoveltyEscalationAttentionPolicy):
    """Evaluation baseline only; deliberately disables rate/repeat protections."""

    def __init__(self, config: AttentionConfig | None = None) -> None:
        super().__init__((config or AttentionConfig()).model_copy(update={"policy": "NAIVE"}))


class CooldownAttentionPolicy(NoveltyEscalationAttentionPolicy):
    def __init__(self, config: AttentionConfig | None = None) -> None:
        super().__init__((config or AttentionConfig()).model_copy(update={"policy": "COOLDOWN"}))
