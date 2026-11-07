"""Bounded single-owner semantic evidence, independent of geometric track identity."""

from collections import deque
from dataclasses import dataclass
from threading import get_ident
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .config import canonical_hash
from .contracts import FrameIdentity
from .perceived_entity import PerceivedEntityObservation, SemanticConcept, SemanticGroup
from .tracking_types import TrackId


class SemanticFusionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)
    evidence_capacity: Annotated[int, Field(ge=3, le=64)] = 16
    provider_capacity: Annotated[int, Field(ge=1, le=16)] = 8
    expiry_ns: Annotated[int, Field(ge=1, le=10_000_000_000)] = 2_000_000_000
    minimum_support: Annotated[int, Field(ge=2, le=16)] = 3
    minimum_agreement: Annotated[float, Field(gt=0.5, le=1)] = 0.7
    minimum_confidence: Annotated[float, Field(ge=0, le=1)] = 0.5


@dataclass(frozen=True)
class SemanticEvidence:
    observation: PerceivedEntityObservation
    received_ns: int


@dataclass(frozen=True)
class TrackSemanticState:
    track_id: TrackId
    selected_concept: SemanticConcept | None
    selected_group: SemanticGroup
    quality: Literal["STABLE", "UNSTABLE", "UNKNOWN", "EXPIRED"]
    confidence_basis: str
    last_observed_ns: int | None
    age_ns: int | None
    valid_until_ns: int | None
    providers: tuple[str, ...]
    evidence: tuple[SemanticEvidence, ...]
    agreement: float
    disagreement: tuple[str, ...]
    configuration_hash: str
    provenance: str = "bounded-track-semantics-v2; NOT_CALIBRATED"
    group_quality: Literal["STABLE", "UNSTABLE", "UNKNOWN"] = "UNKNOWN"
    group_last_observed_ns: int | None = None
    group_valid_until_ns: int | None = None
    group_spoken_label: str | None = None
    calibration_status: str = "UNCALIBRATED"


class TrackSemanticFusion:
    def __init__(
        self, track_id: TrackId, born: FrameIdentity, config: SemanticFusionConfig
    ) -> None:
        if config.minimum_support > config.evidence_capacity:
            raise ValueError("Semantic support exceeds evidence capacity")
        self.track_id, self.born, self.config = track_id, born, config
        self.configuration_hash = canonical_hash(
            {"policy_version": "bounded-track-semantics-v2", "config": config.model_dump()}
        )
        self._owner = get_ident()
        self._now = born.observation_ns
        self._evidence: deque[SemanticEvidence] = deque(maxlen=config.evidence_capacity)
        self._watermarks: dict[str, FrameIdentity] = {}
        self._selected: str | None = None

    def _check(self, now: int) -> None:
        if get_ident() != self._owner or not self._now <= now <= 2**63 - 1:
            raise ValueError("Semantic fusion ownership/time mismatch")

    def observe(self, observation: PerceivedEntityObservation, now: int) -> None:
        self._check(now)
        identity = observation.source_frame
        if (
            identity.source_id != self.born.source_id
            or identity.timing != self.born.timing
            or identity.observation_ns < self.born.observation_ns
            or identity.sequence < self.born.sequence
            or not 0 <= now - identity.observation_ns < self.config.expiry_ns
        ):
            raise ValueError("Semantic evidence source/birth/freshness mismatch")
        previous = self._watermarks.get(observation.provider_id)
        if previous is not None and (
            identity.sequence <= previous.sequence
            or identity.observation_ns <= previous.observation_ns
        ):
            raise ValueError("Duplicate/regressing provider evidence")
        if previous is None and len(self._watermarks) >= self.config.provider_capacity:
            raise ValueError("Semantic provider capacity exceeded")
        self._watermarks[observation.provider_id] = identity
        self._evidence.append(SemanticEvidence(observation, now))
        self._now = now

    def snapshot(self, now: int) -> TrackSemanticState:
        self._check(now)
        self._now = now
        c = self.config
        recent = tuple(
            e
            for e in self._evidence
            if now - e.observation.source_frame.observation_ns < c.expiry_ns
        )
        scores: dict[str, float] = {}
        support: dict[str, set[FrameIdentity]] = {}
        latest: dict[str, PerceivedEntityObservation] = {}
        group_scores: dict[SemanticGroup, float] = {}
        group_support: dict[SemanticGroup, set[FrameIdentity]] = {}
        group_latest: dict[SemanticGroup, PerceivedEntityObservation] = {}
        streams = {
            (
                e.observation.provider_id,
                e.observation.model_version,
                e.observation.provider_configuration_sha256,
                "DETECTOR_JOINT_SCORE"
                if (
                    e.observation.concept.score_basis
                    if e.observation.concept
                    else e.observation.confidence_basis
                )
                in {"JOINT_DETECTION_SCORE", "DETECTOR_JOINT_SCORE"}
                else e.observation.concept.score_basis
                if e.observation.concept
                else e.observation.confidence_basis,
            )
            for e in recent
        }
        for evidence in recent:
            o = evidence.observation
            valid_source = o.quality == "GOOD" or (
                o.source_validity == "VALIDATED_RUNTIME_OUTPUT"
                and o.source_validation_provenance is not None
                and o.quality not in {"UNRELIABLE", "DEGRADED"}
            )
            label = o.concept.normalized_label if o.concept else ""
            weight = o.concept.confidence if o.concept else o.region_confidence
            weight *= (
                1.0
                if valid_source
                else {"GOOD": 1.0, "DEGRADED": 0.5, "UNKNOWN": 0.25, "UNRELIABLE": 0.0}[o.quality]
            )
            weight *= 1 - (now - o.source_frame.observation_ns) / c.expiry_ns
            scores[label] = scores.get(label, 0) + weight
            group_key = (
                o.semantic_resolution.group if o.semantic_resolution else SemanticGroup.UNKNOWN
            )
            group_scores[group_key] = group_scores.get(group_key, 0) + weight
            if (
                valid_source
                and o.concept
                and o.concept.confidence >= c.minimum_confidence
                and group_key != SemanticGroup.UNKNOWN
            ):
                group_support.setdefault(group_key, set()).add(o.source_frame)
                previous_group = group_latest.get(group_key)
                if (
                    previous_group is None
                    or o.source_frame.observation_ns > previous_group.source_frame.observation_ns
                ):
                    group_latest[group_key] = o
            if o.concept and o.concept.confidence >= c.minimum_confidence and valid_source:
                support.setdefault(label, set()).add(o.source_frame)
            if (
                o.concept is not None
                and valid_source
                and o.concept.confidence >= c.minimum_confidence
                and (
                    label not in latest
                    or o.source_frame.observation_ns > latest[label].source_frame.observation_ns
                )
            ):
                latest[label] = o
        total = sum(scores.values())
        winner = min(scores, key=lambda key: (-scores[key], key)) if scores else ""
        stable = bool(
            winner
            and len(streams) <= 1
            and total > 0
            and scores[winner] / total >= c.minimum_agreement
            and len(support.get(winner, set())) >= c.minimum_support
        )
        if self._selected not in latest:
            self._selected = None
        if stable:
            self._selected = winner
        selected = latest.get(self._selected) if self._selected else None
        stamp = selected.source_frame.observation_ns if selected else None
        group = (
            min(group_scores, key=lambda key: (-group_scores[key], key))
            if group_scores
            else SemanticGroup.UNKNOWN
        )
        group_stable = bool(
            group != SemanticGroup.UNKNOWN
            and len(streams) <= 1
            and total > 0
            and group_scores[group] / total >= c.minimum_agreement
            and len(group_support.get(group, set())) >= c.minimum_support
        )
        group_observation = group_latest.get(group) if group_stable else None
        group_stamp = group_observation.source_frame.observation_ns if group_observation else None
        return TrackSemanticState(
            self.track_id,
            selected.concept if selected else None,
            group if group_stable else SemanticGroup.UNKNOWN,
            "STABLE"
            if stable and self._selected == winner
            else "UNSTABLE"
            if any(e.observation.concept for e in recent)
            else "UNKNOWN"
            if recent
            else "EXPIRED"
            if self._evidence
            else "UNKNOWN",
            selected.confidence_basis if selected else "UNAVAILABLE",
            stamp,
            now - stamp if stamp is not None else None,
            stamp + c.expiry_ns if stamp is not None else None,
            tuple(sorted({e.observation.provider_id for e in recent})),
            recent,
            scores.get(self._selected or "", 0) / total if total > 0 and len(streams) <= 1 else 0,
            tuple(sorted(label or "UNKNOWN" for label in scores if label != self._selected)),
            self.configuration_hash,
            group_quality="STABLE" if group_stable else "UNSTABLE" if group_support else "UNKNOWN",
            group_last_observed_ns=group_stamp,
            group_valid_until_ns=group_stamp + c.expiry_ns if group_stamp is not None else None,
            group_spoken_label=(
                group_observation.semantic_resolution.spoken_label
                if group_observation and group_observation.semantic_resolution
                else None
            ),
        )
