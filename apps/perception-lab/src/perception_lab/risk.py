"""Bounded per-entity rule baseline over contracts, never duplicate geometry."""

import hashlib
from collections import defaultdict
from dataclasses import dataclass

from .contracts import ComponentProvenance
from .corridor_types import CorridorAnalysis, EntityCorridorRelation, Relation
from .interaction_types import EntityInteractionForecast, InteractionAnalysis, InteractionLevel
from .risk_config import RiskConfig
from .risk_types import (
    RiskAssessment,
    RiskAssessmentSet,
    RiskFactor,
    RiskLevel,
    RiskQuality,
    RiskTrend,
)
from .trajectory_types import PredictedTrajectory, TrajectorySet
from .world_types import EvidenceSource, EvidenceStatus, WorldEntity, WorldEntityId, WorldState

ORDER = (RiskLevel.LOW, RiskLevel.ELEVATED, RiskLevel.HIGH, RiskLevel.SEVERE)
USABLE = {"GOOD", "DEGRADED"}
OCCUPIED = {Relation.INSIDE, Relation.INTERSECTS}


@dataclass(frozen=True)
class PriorRisk:
    timestamp: int
    level: RiskLevel
    quality: RiskQuality


class RuleBasedRiskEngine:
    """Single pipeline thread owns this instance. History contains one compact prior per ID."""

    def __init__(self, config: RiskConfig) -> None:
        self.config = config
        self.config_hash = hashlib.sha256(config.model_dump_json().encode()).hexdigest()
        self.provenance = ComponentProvenance(
            "rule-based-risk", "risk", configuration_hash=self.config_hash
        )
        self._history: dict[WorldEntityId, PriorRisk] = {}
        self._session: str | None = None
        self._timestamp = -1

    def reset(self) -> None:
        self._history.clear()
        self._session = None
        self._timestamp = -1

    @property
    def history_size(self) -> int:
        return len(self._history)

    def _fresh_source(self, source: EvidenceSource, now: int) -> bool:
        return (
            source.identity is not None
            and source.age_ns is not None
            and source.age_ns == now - source.identity.observation_ns
            and 0 <= source.age_ns <= self.config.max_source_age_ns
            and source.status in {EvidenceStatus.FRESH, EvidenceStatus.DEGRADED}
            and source.quality not in {"UNAVAILABLE", "UNRELIABLE", "FAILED"}
        )

    def assess(
        self,
        state: WorldState,
        corridor: CorridorAnalysis | None,
        trajectories: TrajectorySet | None,
        interaction: InteractionAnalysis | None,
    ) -> RiskAssessmentSet:
        if state.schema_version != 1 or state.state_timestamp < 0:
            raise ValueError("Unsupported world schema or timestamp")
        if len(state.entities) > self.config.max_entities:
            raise ValueError("Risk entity bound exceeded")
        ids = {e.entity_id for e in state.entities}
        if len(ids) != len(state.entities) or any(i.session_id != state.session_id for i in ids):
            raise ValueError("Duplicate or cross-session entity identity")
        if self._session != state.session_id:
            self.reset()
            self._session = state.session_id
        if state.state_timestamp < self._timestamp:
            raise ValueError("Risk clock moved backwards")
        self._timestamp = state.state_timestamp
        self._history = {
            i: p
            for i, p in self._history.items()
            if i in ids and state.state_timestamp - p.timestamp <= self.config.history_retention_ns
        }
        diagnostics = ["UPSTREAM_INTERACTION_LOW_RECALL", "NO_SCENE_SAFETY_VERDICT"]
        relations: dict[WorldEntityId, EntityCorridorRelation] = {}
        if corridor is not None and (
            corridor.schema_version == 1
            and corridor.world_schema_version == state.schema_version
            and corridor.session_id == state.session_id
            and corridor.state_timestamp == state.state_timestamp
            and corridor.corridor.state_timestamp == state.state_timestamp
            and corridor.world_provenance == state.provenance
            and corridor.quality in USABLE
            and corridor.corridor.quality in USABLE
            and self._fresh_source(corridor.corridor.heading_evidence, state.state_timestamp)
        ):
            if len(corridor.entity_relations) > self.config.max_entities:
                raise ValueError("Risk corridor bound exceeded")
            for r in corridor.entity_relations:
                if r.entity_id in relations or r.entity_id not in ids:
                    raise ValueError("Invalid corridor identity")
                if (
                    r.state_timestamp == state.state_timestamp
                    and r.sources
                    and all(self._fresh_source(s, state.state_timestamp) for s in r.sources)
                ):
                    relations[r.entity_id] = r
        else:
            diagnostics.append("CORRIDOR_UNAVAILABLE_OR_MISMATCHED")
        paths: dict[str, PredictedTrajectory] = {}
        if trajectories is not None and (
            trajectories.schema_version == 1
            and trajectories.session_id == state.session_id
            and trajectories.state_timestamp == state.state_timestamp
            and trajectories.world_provenance == state.provenance
        ):
            if len(trajectories.trajectories) > self.config.max_hypotheses:
                raise ValueError("Risk trajectory bound exceeded")
            for path in trajectories.trajectories:
                if path.trajectory_id in paths or path.entity_id not in ids:
                    raise ValueError("Invalid trajectory identity")
                paths[path.trajectory_id] = path
        forecasts: dict[WorldEntityId, list[EntityInteractionForecast]] = defaultdict(list)
        if (
            interaction is not None
            and corridor is not None
            and trajectories is not None
            and (
                interaction.schema_version == 1
                and interaction.session_id == state.session_id
                and interaction.state_timestamp == state.state_timestamp
                and interaction.world_provenance == state.provenance
                and interaction.corridor_provenance == corridor.provenance
                and interaction.trajectory_provenance == trajectories.provenance
                and interaction.quality in USABLE
                and relations
            )
        ):
            if len(interaction.entity_interactions) > self.config.max_hypotheses:
                raise ValueError("Risk interaction bound exceeded")
            seen: set[str] = set()
            for forecast in interaction.entity_interactions:
                if forecast.entity_id not in ids or forecast.trajectory_id in seen:
                    raise ValueError("Invalid interaction identity")
                seen.add(forecast.trajectory_id)
                if forecast.entity_id in relations:
                    forecasts[forecast.entity_id].append(forecast)
        else:
            diagnostics.append("INTERACTION_UNAVAILABLE_OR_MISMATCHED")
        assessments = tuple(
            self._entity(
                state,
                entity,
                relations.get(entity.entity_id),
                forecasts.get(entity.entity_id, []),
                paths,
            )
            for entity in state.entities
        )
        # Bounded level buckets; ties preserve producer order, not a hidden attention decision.
        ranking = tuple(
            a.entity_id for level in reversed(ORDER) for a in assessments if a.risk_level == level
        )
        self._history = {
            a.entity_id: PriorRisk(a.state_timestamp, a.risk_level, a.evidence_quality)
            for a in assessments
        }
        if not assessments:
            diagnostics.append("EMPTY_SET_NOT_SAFE")
        return RiskAssessmentSet(
            state.session_id,
            state.state_timestamp,
            state.state_timestamp + self.config.validity_ns,
            assessments,
            ranking,
            tuple((level, sum(a.risk_level == level for a in assessments)) for level in RiskLevel),
            tuple(diagnostics),
            state.capabilities,
            self.provenance,
            self.config_hash,
            state.provenance,
        )

    def _entity(
        self,
        state: WorldState,
        entity: WorldEntity,
        relation: EntityCorridorRelation | None,
        forecasts: list[EntityInteractionForecast],
        paths: dict[str, PredictedTrajectory],
    ) -> RiskAssessment:
        reasons = [
            "UPSTREAM_INTERACTION_LOW_RECALL",
            "METRIC_DEPTH_UNVALIDATED",
            "PHYSICAL_MOTION_UNVALIDATED",
        ]
        factors: list[RiskFactor] = []
        reducing: list[RiskFactor] = []
        age = state.state_timestamp - entity.latest_observed_ns
        source_age = entity.track_evidence.age_ns
        fresh = (
            entity.state_timestamp == state.state_timestamp
            and 0 <= age <= self.config.max_source_age_ns
            and entity.observation_age_ns == age
            and source_age is not None
            and 0 <= source_age <= self.config.max_source_age_ns
            and entity.track_evidence.status in {EvidenceStatus.FRESH, EvidenceStatus.DEGRADED}
            and self._fresh_source(entity.track_evidence, state.state_timestamp)
            and entity.quality in USABLE
            and state.scene_quality.state in USABLE
        )
        observed = entity.observation_status == "OBSERVED"
        if not fresh:
            reasons.append("STALE_SOURCE_OR_UNAVAILABLE_TRACK")
        if not observed:
            reasons.append("TRACK_PREDICTED_ONLY")
        if any("FRAGMENT" in r or "IDENTITY" in r for r in entity.reasons):
            reasons.append("TRACK_FRAGMENTED")
        semantic = (
            entity.semantic_evidence.validation_status
            if entity.semantic_evidence
            else "UNAVAILABLE"
        )
        if semantic != "VALIDATED":
            reasons.append("SEMANTIC_UNVERIFIED")
        current = fresh and observed and relation is not None and relation.quality in USABLE
        if relation is None or relation.quality != "GOOD":
            reasons.append("CORRIDOR_DEGRADED")
        usable: list[EntityInteractionForecast] = []
        trajectory_age: int | None = None
        for f in forecasts:
            path = paths.get(f.trajectory_id)
            if f.ttc.seconds is not None or f.cpa.time_seconds is not None:
                reasons.append("TTC_CPA_DIAGNOSTIC_ONLY")
            if path is None or path.entity_id != entity.entity_id or not path.source_observations:
                reasons.append("TRAJECTORY_UNAVAILABLE")
                continue
            last = path.source_observations[-1]
            path_age = state.state_timestamp - last.observation_ns
            trajectory_age = max(trajectory_age or 0, path_age)
            if (
                not fresh
                or not observed
                or f.quality not in USABLE
                or path.quality not in USABLE
                or f.state_timestamp != state.state_timestamp
                or path.source_state_timestamp != state.state_timestamp
                or path.prediction_start_timestamp != state.state_timestamp
                or entity.track_evidence.identity is None
                or last.source_id != entity.track_evidence.identity.source_id
                or not 0 <= path_age <= self.config.max_source_age_ns
                or f.physical_validity not in {InteractionLevel.IMAGE, InteractionLevel.WORLD}
                or not 0 < f.horizon_ns <= 3_000_000_000
                or any(
                    a is not None and (a < 0 or a > self.config.max_source_age_ns)
                    for name, a in f.source_ages
                    if name in {"track", "trajectory"}
                )
            ):
                reasons.append("TRAJECTORY_UNRELIABLE")
                continue
            usable.append(f)
        occupied = bool(current and relation is not None and relation.relation in OCCUPIED)
        entries = [
            f
            for f in usable
            if f.predicted_corridor_entry_time_ns is not None
            and 0 <= f.predicted_corridor_entry_time_ns <= f.horizon_ns
            and f.interaction_type in {"PREDICTED_ENTER", "CROSS_CORRIDOR", "PREDICTED_ENTER_EXIT"}
        ]
        possible = any(f.envelope_interaction == "POSSIBLE_INTERSECTION" for f in usable)
        receding = bool(usable) and all(f.approach_evidence.state == "RECEDING" for f in usable)
        level = RiskLevel.UNDETERMINED
        tier: InteractionLevel | None = None
        if occupied:
            level = RiskLevel.ELEVATED if receding else RiskLevel.HIGH
            reasons.append("CURRENTLY_INSIDE_CORRIDOR")
            factors.append(
                RiskFactor("CURRENT_CORRIDOR_OCCUPANCY", "SUPPORTING", "corridor", "occupied")
            )
            tier = (
                InteractionLevel.IMAGE
                if relation and relation.coordinate_basis == "IMAGE_SPACE_RELATION"
                else InteractionLevel.WORLD
            )
        elif entries:
            earliest = min(f.predicted_corridor_entry_time_ns or 0 for f in entries)
            level = (
                RiskLevel.HIGH if earliest <= self.config.urgent_entry_ns else RiskLevel.ELEVATED
            )
            reasons.append("PREDICTED_CROSSING")
            factors.append(
                RiskFactor("PREDICTED_CORRIDOR_ENTRY", "SUPPORTING", "interaction", str(earliest))
            )
            tier = entries[0].physical_validity
        elif possible:
            level = RiskLevel.ELEVATED
            reasons.append("POSSIBLE_CORRIDOR_ENTRY")
            factors.append(
                RiskFactor(
                    "POSSIBLE_CORRIDOR_ENTRY", "SUPPORTING", "interaction", "uncalibrated envelope"
                )
            )
            tier = usable[0].physical_validity
        elif (
            current
            and relation is not None
            and relation.relation == Relation.OUTSIDE
            and usable
            and len(usable) == len(forecasts)
            and all(
                f.interaction_type == "REMAIN_OUTSIDE"
                and f.envelope_interaction == "NO_INTERSECTION_WITHIN_ENVELOPE"
                for f in usable
            )
        ):
            level = RiskLevel.LOW
            reasons.append("REMAINS_OUTSIDE_MODELED_CORRIDOR")
            reducing.append(
                RiskFactor("OUTSIDE_MODELED_CORRIDOR", "REDUCING", "interaction", "not safety")
            )
            tier = usable[0].physical_validity
        if receding:
            reasons.append("RECEDING")
            reducing.append(
                RiskFactor("RECEDING_FROM_CORRIDOR", "REDUCING", "interaction", "geometric")
            )
        if not usable:
            reasons.append("FUTURE_INTERACTION_UNAVAILABLE")
        if occupied and any(f.approach_evidence.state == "STATIONARY_OR_LATERAL" for f in usable):
            reasons.append("STATIC_OR_STABLE_IN_CORRIDOR")
        if level == RiskLevel.UNDETERMINED:
            reasons.append("INSUFFICIENT_EVIDENCE")
        # Global coverage and sensing limitations mean this prototype never declares GOOD quality.
        quality = (
            RiskQuality.INSUFFICIENT if level == RiskLevel.UNDETERMINED else RiskQuality.DEGRADED
        )
        prior = self._history.get(entity.entity_id)
        trend = RiskTrend.UNKNOWN
        if (
            prior is not None
            and prior.timestamp < state.state_timestamp
            and prior.level in ORDER
            and level in ORDER
            and state.state_timestamp - prior.timestamp <= self.config.validity_ns
        ):
            delta = ORDER.index(level) - ORDER.index(prior.level)
            trend = (
                RiskTrend.RISING
                if delta > 0
                else RiskTrend.FALLING
                if delta < 0
                else RiskTrend.STABLE
            )
        return RiskAssessment(
            entity.entity_id,
            state.state_timestamp,
            state.state_timestamp + self.config.validity_ns,
            level,
            quality,
            tuple(factors),
            tuple(reducing),
            tuple(dict.fromkeys(f.interaction_type for f in forecasts)),
            tier,
            (
                ("track", age),
                ("depth", entity.depth_evidence.age_ns),
                ("trajectory", trajectory_age),
                ("interaction", 0 if usable else None),
                ("corridor", 0 if current else None),
            ),
            tuple(dict.fromkeys(reasons)),
            trend,
            (state.provenance, self.provenance),
            self.config_hash,
            semantic,
        )
