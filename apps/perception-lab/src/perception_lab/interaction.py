"""Trajectory-first, stateless interaction evidence with explicit coordinate/validity gates."""

from math import isfinite

from . import __version__
from .config import canonical_hash
from .contracts import ComponentProvenance, TimingProvenance
from .corridor_types import CorridorAnalysis, CorridorMode, Point2
from .geometry import CoreGeometry
from .interaction_config import InteractionConfig
from .interaction_geometry import segment, unsigned_distance, validate_polygon
from .interaction_motion import candidates
from .interaction_types import (
    ApproachEvidence,
    CorridorClosestApproach,
    EntityInteractionForecast,
    InteractionAnalysis,
    InteractionLevel,
    InteractionSample,
    ReferenceMotion,
)
from .trajectory_types import (
    PredictedTrajectory,
    TrajectoryDomain,
    TrajectoryPhysicalStatus,
    TrajectorySet,
)
from .world_types import EvidenceStatus, WorldEntity, WorldState


def worst(*qualities: str) -> str:
    order = {
        "GOOD": 0,
        "VALID": 0,
        "DEGRADED": 1,
        "PARTIAL": 1,
        "UNRELIABLE": 2,
        "UNAVAILABLE": 3,
        "FAILED": 3,
    }
    score = max(order.get(q, 2) for q in qualities)
    return ("GOOD", "DEGRADED", "UNRELIABLE", "UNAVAILABLE")[score]


class TrajectoryCorridorInteractionAnalyzer:
    def __init__(self, config: InteractionConfig, geometry: CoreGeometry | None = None) -> None:
        self.config, self.geometry = config, geometry
        self.calibration_id = (
            canonical_hash(geometry.c.model_dump(exclude={"metadata"})) if geometry else None
        )
        self.provenance = ComponentProvenance(
            "TrajectoryCorridorInteractionAnalyzer",
            "interaction",
            "deterministic-v1",
            __version__,
            "python+guardian",
            canonical_hash(config.model_dump()),
        )

    def analyze(
        self,
        state: WorldState,
        corridor: CorridorAnalysis,
        trajectories: TrajectorySet,
        reference: ReferenceMotion | None = None,
    ) -> InteractionAnalysis:
        if (
            state.schema_version != 1
            or corridor.schema_version != 1
            or trajectories.schema_version != 1
            or state.session_id != corridor.session_id
            or state.session_id != trajectories.session_id
            or state.state_timestamp != corridor.state_timestamp
            or state.state_timestamp != corridor.corridor.state_timestamp
            or state.state_timestamp != trajectories.state_timestamp
            or state.state_timestamp < 0
            or corridor.world_provenance != state.provenance
            or trajectories.world_provenance != state.provenance
            or corridor.world_schema_version != state.schema_version
            or (
                corridor.calibration_id is not None
                and corridor.calibration_id != state.camera_state.calibration_id
            )
        ):
            raise ValueError(
                "Interaction requires matching schema, session, source time and world provenance"
            )
        if len(state.entities) > 512 or len(trajectories.trajectories) > 2048:
            raise ValueError("Interaction capacity exceeded")
        entities = {e.entity_id: e for e in state.entities}
        if len(entities) != len(state.entities) or any(
            e.entity_id.session_id != state.session_id for e in state.entities
        ):
            raise ValueError("Duplicate or cross-session entity")
        ids = set()
        results = []
        unavailable = []
        for t in trajectories.trajectories:
            if t.trajectory_id in ids or t.entity_id not in entities:
                raise ValueError("Duplicate trajectory or unknown entity")
            ids.add(t.trajectory_id)
            e = entities[t.entity_id]
            self._validate(t, e, state)
            if not t.samples or t.samples[0].horizon_ns > self.config.horizon_ns:
                unavailable.append((e.entity_id, "NO_SAMPLES_WITHIN_HORIZON"))
                continue
            results.append(self._forecast(t, e, state, corridor, reference))
        represented = {r.entity_id for r in results}
        unavailable.extend(
            (e.entity_id, "NO_USABLE_TRAJECTORY")
            for e in state.entities
            if e.entity_id not in represented
        )
        return InteractionAnalysis(
            state.session_id,
            state.state_timestamp,
            tuple(results),
            corridor.provenance,
            trajectories.provenance,
            state.provenance,
            self.provenance,
            worst(*(r.quality for r in results)) if results else "UNAVAILABLE",
            (
                "FROZEN_CORRIDOR_ASSUMPTION",
                "NOT_COLLISION_OR_RISK",
                "USER_PHYSICAL_MOTION_UNVALIDATED",
            ),
            tuple(unavailable),
        )

    def _validate(self, t: PredictedTrajectory, e: WorldEntity, state: WorldState) -> None:
        dimension, units = {
            TrajectoryDomain.IMAGE: (2, "pixels"),
            TrajectoryDomain.BEARING: (2, "radians"),
            TrajectoryDomain.WORLD: (3, "meters"),
        }[t.coordinate_space]
        expected = {
            TrajectoryDomain.IMAGE: TrajectoryPhysicalStatus.IMAGE_ONLY,
            TrajectoryDomain.BEARING: TrajectoryPhysicalStatus.CAMERA_RELATIVE,
            TrajectoryDomain.WORLD: TrajectoryPhysicalStatus.WORLD_RESEARCH_UNVALIDATED,
        }[t.coordinate_space]
        if t.physical_status != expected:
            raise ValueError("Unsupported domain/physical-validity combination")
        if (
            t.source_state_timestamp != state.state_timestamp
            or t.prediction_start_timestamp != state.state_timestamp
            or e.state_timestamp != state.state_timestamp
            or t.units != units
            or not t.frame_id
            or len(t.origin) != dimension
            or len(t.velocity) != dimension
            or len(t.samples) > 8
            or len(t.source_observations) > 34
        ):
            raise ValueError("Invalid trajectory identity, dimensions, units or bounds")
        previous = 0
        for s in t.samples:
            if (
                s.horizon_ns <= previous
                or s.horizon_ns > 3_000_000_000
                or s.timestamp_ns != state.state_timestamp + s.horizon_ns
                or len(s.position) != dimension
                or not isfinite(s.envelope_radius)
                or not 0 <= s.envelope_radius <= 1e9
            ):
                raise ValueError("Invalid prediction horizon or envelope")
            previous = s.horizon_ns
        if any(
            not isfinite(v) or abs(v) > 1e9
            for p in (t.origin, t.velocity, *(s.position for s in t.samples))
            for v in p
        ):
            raise ValueError("Non-finite or unbounded trajectory")
        source = e.track_evidence.identity
        if source is None or source.timing == TimingProvenance.UNKNOWN:
            raise ValueError("Unknown source clock")
        if any(
            h.source_id != source.source_id
            or h.timing != source.timing
            or h.observation_ns > state.state_timestamp
            for h in t.source_observations
        ):
            raise ValueError("Mixed-clock or future source")
        if not t.source_observations or any(
            a.observation_ns >= b.observation_ns
            for a, b in zip(t.source_observations, t.source_observations[1:], strict=False)
        ):
            raise ValueError("Ordered observed trajectory sources required")

    def _forecast(
        self,
        t: PredictedTrajectory,
        e: WorldEntity,
        state: WorldState,
        analysis: CorridorAnalysis,
        reference: ReferenceMotion | None,
    ) -> EntityInteractionForecast:
        c, cfg = analysis.corridor, self.config
        samples = tuple(s for s in t.samples if s.horizon_ns <= cfg.horizon_ns)
        horizon = samples[-1].horizon_ns
        level = {
            TrajectoryDomain.IMAGE: InteractionLevel.IMAGE,
            TrajectoryDomain.BEARING: InteractionLevel.BEARING,
            TrajectoryDomain.WORLD: InteractionLevel.WORLD,
        }[t.coordinate_space]
        quality = worst(
            t.quality,
            e.quality,
            state.scene_quality.state,
            analysis.quality,
            c.quality,
            *(s.quality for s in samples),
        )
        reasons = [*t.reasons, *e.reasons, *c.reasons]
        age = state.state_timestamp - e.latest_observed_ns
        if age < 0 or e.observation_age_ns != age:
            raise ValueError("Invalid observation age")
        stale = (
            age > cfg.max_age_ns
            or state.state_timestamp - t.source_observations[-1].observation_ns > cfg.max_age_ns
            or e.track_evidence.status
            in {EvidenceStatus.STALE, EvidenceStatus.FAILED, EvidenceStatus.UNAVAILABLE}
            or e.lifecycle.value == "LOST"
        )
        if stale:
            quality = "UNAVAILABLE"
            reasons.append("SOURCE_STALE_OR_UNAVAILABLE")
        if e.observation_status != "OBSERVED":
            quality = worst(quality, "UNRELIABLE")
            reasons.append("TRACK_PREDICTED")
        assumptions = [
            "FROZEN_CORRIDOR_ASSUMPTION",
            "POINT_PATH_NOT_OBJECT_VOLUME",
            "PIECEWISE_LINEAR_MODEL",
            "UNCALIBRATED_ENVELOPE_NOT_PROBABILITY",
        ]
        polygon: tuple[Point2, ...] = ()
        positions: tuple[Point2, ...] = ()
        tolerance = cfg.near_boundary_pixels
        if (
            not stale
            and c.quality not in {"UNAVAILABLE", "FAILED"}
            and t.motion_basis == "OBSERVED_HISTORY"
        ):
            if (
                t.coordinate_space == TrajectoryDomain.IMAGE
                and state.image_geometry
                and t.frame_id == state.image_geometry.camera_image_id
                and (c.mode != CorridorMode.IMAGE or c.zone.coordinate_frame == t.frame_id)
            ):
                polygon = c.image_polygon
                positions = tuple((p[0], p[1]) for p in (t.origin, *(s.position for s in samples)))
            elif (
                t.coordinate_space == TrajectoryDomain.WORLD
                and c.mode == CorridorMode.WORLD
                and c.zone.coordinate_frame == t.frame_id
                and c.origin is not None
                and c.forward is not None
                and c.lateral is not None
            ):
                origin, forward, lateral = c.origin, c.forward, c.lateral
                if (
                    any(not isfinite(v) for p in (origin, forward, lateral) for v in p)
                    or abs(sum(v * v for v in forward) - 1) > 1e-6
                    or abs(sum(v * v for v in lateral) - 1) > 1e-6
                    or abs(sum(a * b for a, b in zip(forward, lateral, strict=True))) > 1e-6
                ):
                    raise ValueError("Invalid corridor plane basis")

                def plane(p: tuple[float, ...]) -> Point2:
                    delta = tuple(a - b for a, b in zip(p, origin, strict=True))
                    return sum(a * b for a, b in zip(delta, lateral, strict=True)), sum(
                        a * b for a, b in zip(delta, forward, strict=True)
                    )

                polygon = tuple(plane(p) for p in c.zone.polygon)
                positions = tuple(plane(p) for p in (t.origin, *(s.position for s in samples)))
                tolerance = cfg.near_boundary_meters
                assumptions.append("GROUND_PLANE_PROJECTION_NOT_3D_CLEARANCE")
        intervals: list[tuple[int, int]] = []
        output: list[InteractionSample] = []
        closest = None
        current = future = "UNKNOWN"
        interaction = envelope = direction = longitudinal = "UNKNOWN"
        entry = exit_time = None
        approach = ApproachEvidence(
            "UNAVAILABLE", "CURRENT_CORRIDOR", t.frame_id, t.units, None, None, "UNAVAILABLE"
        )
        if polygon:
            validate_polygon(polygon)
            distances = tuple(unsigned_distance(p, polygon) for p in positions)
            current = (
                "INSIDE"
                if distances[0] == 0
                else "NEAR_BOUNDARY"
                if distances[0] <= tolerance
                else "OUTSIDE"
            )
            best = (distances[0], 0)
            previous = 0
            possible = False
            for i, s in enumerate(samples):
                hit, minimum, fraction = segment(positions[i], positions[i + 1], polygon)
                time = previous + round(fraction * (s.horizon_ns - previous))
                best = min(best, (minimum, time))
                radius = max(s.envelope_radius, samples[max(0, i - 1)].envelope_radius)
                possible |= minimum <= radius
                if hit is not None:
                    start = previous + round(hit[0] * (s.horizon_ns - previous))
                    end = previous + round(hit[1] * (s.horizon_ns - previous))
                    if intervals and start <= intervals[-1][1]:
                        intervals[-1] = (intervals[-1][0], max(end, intervals[-1][1]))
                    else:
                        intervals.append((start, end))
                distance = distances[i + 1]
                relation = (
                    "INSIDE"
                    if distance == 0
                    else "NEAR_BOUNDARY"
                    if distance <= tolerance
                    else "OUTSIDE"
                )
                output.append(
                    InteractionSample(
                        s.horizon_ns, s.position, relation, distance, worst(quality, s.quality)
                    )
                )
                previous = s.horizon_ns
            future = output[-1].corridor_relation
            entry = intervals[0][0] if intervals else None
            exit_time = intervals[0][1] if intervals and intervals[0][1] < horizon else None
            envelope = (
                "NOMINAL_INTERSECTION"
                if intervals
                else "POSSIBLE_INTERSECTION"
                if possible
                else "NO_INTERSECTION_WITHIN_ENVELOPE"
            )
            if not intervals and t.uncertainty_status != "UNCALIBRATED_RESEARCH_ENVELOPE":
                envelope = "UNKNOWN"
            interaction = (
                "REMAIN_INSIDE"
                if current == "INSIDE" and exit_time is None
                else "PREDICTED_EXIT"
                if current == "INSIDE"
                else "CROSS_CORRIDOR"
                if entry is not None and exit_time is not None
                else "PREDICTED_ENTER"
                if entry is not None
                else "PASS_NEAR"
                if best[0] <= tolerance
                else "REMAIN_OUTSIDE"
            )
            left, right = min(p[0] for p in polygon), max(p[0] for p in polygon)
            if interaction == "CROSS_CORRIDOR" and not (
                positions[0][0] < left
                and positions[-1][0] > right
                or positions[0][0] > right
                and positions[-1][0] < left
            ):
                interaction = "PREDICTED_ENTER_EXIT"
            direction = (
                "LEFT_TO_RIGHT"
                if positions[-1][0] - positions[0][0] > tolerance
                else "RIGHT_TO_LEFT"
                if positions[-1][0] - positions[0][0] < -tolerance
                else "UNKNOWN"
            )
            if level == InteractionLevel.WORLD:
                longitudinal = "BEHIND" if positions[0][1] < 0 else "AHEAD"
            delta = distances[-1] - distances[0]
            approach_state = (
                "APPROACHING"
                if delta < -tolerance
                else "RECEDING"
                if delta > tolerance
                else "INDETERMINATE"
                if best[0] < distances[0] - tolerance
                else "STATIONARY_OR_LATERAL"
            )
            approach = ApproachEvidence(
                approach_state,
                "CURRENT_FROZEN_CORRIDOR",
                t.frame_id,
                t.units,
                distances[0],
                distances[-1],
                quality,
            )
            closest = CorridorClosestApproach(best[0], best[1], t.frame_id, t.units, level, quality)
        else:
            reasons.append("CORRIDOR_COORDINATE_MAPPING_UNAVAILABLE")
        if (
            t.coordinate_space == TrajectoryDomain.BEARING
            and not stale
            and t.frame_id == state.camera_state.calibration_id
        ):
            initial, final = abs(t.origin[0]), abs(samples[-1].position[0])
            approach = ApproachEvidence(
                "APPROACHING"
                if final < initial - cfg.bearing_tolerance_radians
                else "RECEDING"
                if final > initial + cfg.bearing_tolerance_radians
                else "STATIONARY_OR_LATERAL",
                "CAMERA_FORWARD_BEARING_NOT_RANGE",
                t.frame_id,
                "radians",
                initial,
                final,
                quality,
            )
        ttc, cpa = candidates(
            t, e, state, horizon, cfg, self.geometry, reference, level, quality, self.calibration_id
        )
        diagnostics = []
        if ttc.seconds is not None and polygon and not intervals:
            diagnostics.append("FINITE_TTC_BUT_NO_CORRIDOR_INTERSECTION")
        if intervals and ttc.seconds is None:
            diagnostics.append("CORRIDOR_INTERSECTION_BUT_TTC_UNAVAILABLE")
        if level == InteractionLevel.WORLD:
            diagnostics.append("PHYSICAL_INPUT_UNVALIDATED")
        return EntityInteractionForecast(
            e.entity_id,
            t.trajectory_id,
            state.state_timestamp,
            horizon,
            current,
            future,
            interaction,
            tuple(intervals),
            entry,
            exit_time,
            None,
            None,
            envelope,
            closest,
            approach,
            tuple(output),
            ttc,
            cpa,
            level,
            quality,
            tuple(dict.fromkeys(reasons))[:32],
            (("track", age), *state.source_ages[:16]),
            tuple(assumptions),
            (*t.provenance, analysis.provenance, self.provenance),
            tuple(diagnostics),
            direction,
            longitudinal,
        )
