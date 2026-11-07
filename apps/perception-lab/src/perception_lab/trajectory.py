"""Stateless causal predictions from bounded observed histories, never fed upstream."""

from dataclasses import replace
from math import dist, isfinite, pi

from .config import canonical_hash
from .contracts import ComponentProvenance, TimingProvenance
from .corridor_types import CorridorAnalysis
from .depth import DepthKind
from .geometry import CoreGeometry
from .trajectory_config import TrajectoryConfig
from .trajectory_fit import linear_fit
from .trajectory_types import (
    PredictedTrajectory,
    TrajectorySample,
    TrajectorySet,
)
from .trajectory_types import (
    TrajectoryDomain as D,
)
from .trajectory_types import (
    TrajectoryPhysicalStatus as P,
)
from .world_types import EntityHistory, WorldEntity, WorldState
from .world_types import EvidenceStatus as S


class AdaptiveKinematicPredictor:
    def __init__(self, config: TrajectoryConfig, geometry: CoreGeometry | None = None) -> None:
        self.config, self.geometry = config, geometry
        self.calibration_hash = (
            canonical_hash(geometry.c.model_dump(exclude={"metadata"})) if geometry else None
        )
        self.hash = canonical_hash(config.model_dump())
        self.provenance = ComponentProvenance(
            "AdaptiveKinematicPredictor",
            "trajectory",
            "bounded-kinematic-v1",
            "1",
            "python",
            self.hash,
        )

    def predict(self, state: WorldState, corridor: CorridorAnalysis | None = None) -> TrajectorySet:
        from .trajectory_corridor import relate

        if (
            state.schema_version != 1
            or not state.session_id
            or not 0 <= state.state_timestamp <= 2**63 - 1 - 3_000_000_000
        ):
            raise ValueError("Invalid world schema/session/time")
        if len(state.entities) > 512 or len({e.entity_id for e in state.entities}) != len(
            state.entities
        ):
            raise ValueError("Bounded unique entities required")
        if corridor is not None and (
            corridor.schema_version != 1
            or corridor.session_id != state.session_id
            or corridor.state_timestamp != state.state_timestamp
            or corridor.calibration_id != state.camera_state.calibration_id
        ):
            raise ValueError("Corridor/world identity mismatch")
        trajectories, preferred, unavailable = [], [], []
        for e in state.entities:
            if (
                e.entity_id.session_id != state.session_id
                or e.source_track_id.session_id != state.session_id
                or e.state_timestamp > state.state_timestamp
                or len(e.history) > 128
            ):
                raise ValueError("Invalid entity session/time/history")
            history = self._history(e, state)
            if not history:
                unavailable.append((e.entity_id, "NO_FRESH_OBSERVED_HISTORY"))
                continue
            domain_outputs = []
            for domain in (D.IMAGE, D.BEARING, D.WORLD):
                output = self._domain(e, state, history, domain)
                if output is not None:
                    domain_outputs.append(output)
                else:
                    unavailable.append((e.entity_id, domain.value + "_UNAVAILABLE"))
            trajectories.extend(domain_outputs)
            if domain_outputs:
                # Explicit representation preference, never an accuracy ranking.
                preferred.append(domain_outputs[-1].trajectory_id)
                residual = self._residual(e, state, domain_outputs[0])
                if residual is not None:
                    trajectories.append(residual)
        return TrajectorySet(
            state.session_id,
            state.state_timestamp,
            tuple(trajectories),
            tuple(preferred),
            tuple(relate(t, corridor) for t in trajectories) if corridor else (),
            tuple(unavailable),
            self.provenance,
            state.provenance,
            ("PREDICTIONS_NOT_OBSERVATIONS", "CAMERA_MOTION_UNVALIDATED"),
        )

    def _residual(
        self, e: WorldEntity, state: WorldState, raw: PredictedTrajectory
    ) -> PredictedTrajectory | None:
        """Alternate stabilized-view hypothesis, not a raw future-camera prediction."""
        motion = e.image_motion
        if (
            raw.coordinate_space != D.IMAGE
            or motion is None
            or e.observation_status != "OBSERVED"
            or motion.track_id != e.source_track_id
            or motion.pair.session_id != state.session_id
            or motion.pair.b != e.track_evidence.identity
            or motion.pair.b.observation_ns != state.state_timestamp
            or state.image_geometry is None
            or motion.pair.camera_image_id != state.image_geometry.camera_image_id
            or (motion.pair.width, motion.pair.height)
            != (state.image_geometry.width, state.image_geometry.height)
            or motion.pair.calibration_hash != state.camera_state.calibration_id
            or state.camera_state.calibration_quality not in {"VALID", "DEGRADED"}
            or e.motion_evidence.status not in {S.FRESH, S.DEGRADED}
            or motion.compensation
            not in {"ROTATION_ONLY", "DEPTH_SCALED_RESEARCH_UNVALIDATED_SCALE"}
            or motion.samples < 3
            or motion.pair.dt_seconds <= 0
            or min(motion.mad_pixels) < 0
            or not 0 < motion.valid_fraction <= 1
            or not all(
                isfinite(v) for v in (*motion.median_rate_pixels_per_second, *motion.mad_pixels)
            )
        ):
            return None
        velocity = motion.median_rate_pixels_per_second
        sources = tuple(
            sorted(
                set((*raw.source_observations, motion.pair.a, motion.pair.b)),
                key=lambda identity: identity.observation_ns,
            )
        )
        return replace(
            raw,
            trajectory_id=raw.trajectory_id + ":residual",
            frame_id=raw.frame_id + ":stabilized-research",
            velocity=velocity,
            model="RESIDUAL_RATE_RESEARCH",
            source_observations=sources,
            source_observation_count=len(sources),
            history_span_ns=sources[-1].observation_ns - sources[0].observation_ns,
            quality="UNRELIABLE",
            motion_basis="CAMERA_STABILIZED_RESEARCH_NOT_FUTURE_RAW_PIXELS",
            reasons=(
                *raw.reasons,
                "FUTURE_CAMERA_MOTION_UNKNOWN",
                "LOCAL_FLOW_NOT_OBJECT_CENTER_VELOCITY",
            ),
            samples=tuple(
                replace(
                    s,
                    position=tuple(
                        p + v * s.horizon_ns / 1e9
                        for p, v in zip(raw.origin, velocity, strict=True)
                    ),
                    quality="UNRELIABLE",
                    envelope_radius=s.envelope_radius + max(motion.mad_pixels),
                )
                for s in raw.samples
            ),
            provenance=(*raw.provenance, *e.motion_evidence.provenance),
        )

    def _history(self, e: WorldEntity, state: WorldState) -> tuple[EntityHistory, ...]:
        now, cfg = state.state_timestamp, self.config
        previous = -1
        previous_sequence = -1
        reference = e.track_evidence.identity
        if reference is None or reference.timing == TimingProvenance.UNKNOWN:
            return ()
        out: list[EntityHistory] = []
        for h in e.history:
            t = h.identity.observation_ns
            if (
                t <= previous
                or h.identity.sequence <= previous_sequence
                or t > now
                or t > e.state_timestamp
                or reference is None
                or h.identity.source_id != reference.source_id
                or h.identity.timing != reference.timing
            ):
                raise ValueError("Regressing/future/mixed-clock history")
            previous = t
            previous_sequence = h.identity.sequence
            if h.observation_status != "OBSERVED" or now - t > cfg.history_ns:
                continue
            if not isfinite(h.quality) or not 0 <= h.quality <= 1:
                raise ValueError("Invalid history quality")
            if h.quality <= 0:
                continue
            if out and t - out[-1].identity.observation_ns > cfg.max_gap_ns:
                out.clear()
            out.append(h)
        if (
            not out
            or now - out[-1].identity.observation_ns > cfg.max_age_ns
            or e.track_evidence.status in {S.FAILED, S.UNAVAILABLE, S.STALE}
        ):
            return ()
        return tuple(out[-cfg.history_count :])

    def _domain(
        self, e: WorldEntity, state: WorldState, history: tuple[EntityHistory, ...], domain: D
    ) -> PredictedTrajectory | None:
        cfg = self.config
        rows: list[tuple[EntityHistory, tuple[float, ...]]] = []
        frame, units, physical, floor = "", "", P.IMAGE_ONLY, cfg.pixel_floor
        for h in history:
            point: tuple[float, ...] | None = None
            if domain == D.IMAGE and state.image_geometry is not None:
                point = ((h.box.x1 + h.box.x2) / 2, h.box.y2)
                frame, units = state.image_geometry.camera_image_id, "pixels"
            elif domain == D.BEARING and state.camera_state.calibration_quality in {
                "VALID",
                "DEGRADED",
            }:
                point = (
                    h.bearing_radians
                    if h.calibration_id == state.camera_state.calibration_id
                    else None
                )
                frame, units, physical, floor = (
                    state.camera_state.calibration_id or "",
                    "radians",
                    P.CAMERA_RELATIVE,
                    cfg.bearing_floor,
                )
                if point and any(abs(x) > pi for x in point):
                    point = None
            elif domain == D.WORLD and self.geometry is not None:
                wp = h.world_point
                if (
                    state.camera_state.pose is not None
                    and state.camera_state.pose_evidence.status == S.FRESH
                    and state.camera_state.pose.identity.observation_ns == state.state_timestamp
                    and state.camera_state.calibration_id == self.calibration_hash
                    and wp is not None
                    and h.calibration_id == state.camera_state.calibration_id
                    and wp.world_frame_id == state.camera_state.pose.world_frame_id
                    and wp.identity == h.identity
                    and wp.camera_point.identity == h.identity
                    and wp.camera_point.depth.identity == h.identity
                    and wp.camera_point.depth.representation.kind == DepthKind.METRIC
                    and wp.camera_point.position_meters[2] > 0
                    and wp.camera_point.depth.quality not in {"UNAVAILABLE", "UNRELIABLE"}
                    and h.depth_kind == "METRIC"
                    and wp.camera_point.calibration_quality in {"VALID", "DEGRADED"}
                    and state.camera_state.calibration_quality in {"VALID", "DEGRADED"}
                    and len(h.position_sources) >= 2
                    and {s.subsystem for s in h.position_sources} >= {"depth", "pose"}
                    and all(
                        s.identity == h.identity
                        and s.status == S.FRESH
                        and s.quality != "UNRELIABLE"
                        for s in h.position_sources
                    )
                ):
                    if frame and frame != wp.world_frame_id:
                        rows.clear()
                    point = wp.position_meters
                    frame, units, physical, floor = (
                        wp.world_frame_id,
                        "meters",
                        P.WORLD_RESEARCH_UNVALIDATED,
                        cfg.world_floor,
                    )
            if point is not None:
                if not all(isfinite(v) for v in point):
                    raise ValueError("Non-finite trajectory observation")
                if rows and (
                    h.identity.observation_ns - rows[-1][0].identity.observation_ns > cfg.max_gap_ns
                    or (domain == D.BEARING and dist(point, rows[-1][1]) > pi)
                ):
                    rows.clear()
                rows.append((h, point))
        if (
            not rows
            or not frame
            or state.state_timestamp - rows[-1][0].identity.observation_ns > cfg.max_age_ns
        ):
            return None
        now = state.state_timestamp
        times = tuple((h.identity.observation_ns - now) / 1e9 for h, _ in rows)
        points = tuple(p for _, p in rows)
        position, velocity = points[-1], (0.0,) * len(points[-1])
        residual, rejected, model = 0.0, 0, "CONSTANT_POSITION"
        kept = tuple(range(len(rows)))
        reasons = [
            "IMAGE_SPACE_ONLY"
            if domain == D.IMAGE
            else "CAMERA_RELATIVE"
            if domain == D.BEARING
            else "METRIC_DEPTH_UNVALIDATED",
            "EGO_MOTION_UNVALIDATED",
        ]
        span = rows[-1][0].identity.observation_ns - rows[0][0].identity.observation_ns
        if len(rows) >= cfg.min_observations and span >= cfg.min_span_ns:
            fit = linear_fit(
                times, points, floor, cfg.outlier_multiplier, cfg.model == "CV_LAST_TWO"
            )
            residual, kept = fit.residual, fit.kept
            rejected = len(rows) - len(kept) if cfg.model != "CV_LAST_TWO" else 0
            if rejected:
                reasons.append("MOTION_OUTLIER")
            stable = (
                len(kept) >= (2 if cfg.model == "CV_LAST_TWO" else cfg.min_observations)
                and residual <= cfg.outlier_multiplier * floor
            )
            moving = dist((0.0,) * len(fit.velocity), fit.velocity) * span / 1e9 > floor
            if stable and cfg.model != "CONSTANT_POSITION" and (moving or cfg.model != "ADAPTIVE"):
                position, velocity, model = (
                    fit.position,
                    fit.velocity,
                    "CV_LAST_TWO" if cfg.model == "CV_LAST_TWO" else "CV_WINDOW",
                )
                # Fit position is at last source time. Advance to the prediction start once.
                position = tuple(
                    p + v * (-times[-1]) for p, v in zip(position, velocity, strict=True)
                )
            elif stable:
                position = fit.position
                reasons.append("STATIONARY_HYPOTHESIS")
            else:
                # Do not anchor the fallback on a rejected newest observation.
                position = points[kept[-1]]
                reasons.append("HIGH_FIT_RESIDUAL")
        else:
            reasons.append("INSUFFICIENT_HISTORY")
        quality = "DEGRADED"
        if (
            e.observation_status != "OBSERVED"
            or e.quality in {"UNAVAILABLE", "UNRELIABLE"}
            or state.scene_quality.state in {"UNAVAILABLE", "UNRELIABLE"}
            or rejected
            or "HIGH_FIT_RESIDUAL" in reasons
            or min(h.quality for h, _ in rows) < 0.25
        ):
            quality = "UNRELIABLE"
        if e.observation_status != "OBSERVED":
            reasons.append("TRACK_PREDICTED")
        age = -times[-1]
        base = floor + residual + floor * age
        if quality == "UNRELIABLE":
            base *= 2
        predictions = tuple(
            tuple(p + v * h / 1e9 for p, v in zip(position, velocity, strict=True))
            for h in cfg.horizons_ns
        )
        if not all(isfinite(v) for p in predictions for v in p):
            raise ValueError("Non-finite extrapolation")
        if domain == D.WORLD:
            assert self.geometry is not None
            predictions = self.geometry.predict_world_points(
                frame, state.session_id, now, position, velocity, cfg.horizons_ns
            )
        samples = tuple(
            TrajectorySample(
                h,
                now + h,
                p,
                base * (1 + cfg.growth_per_second * h / 1e9),
                "UNRELIABLE" if h > cfg.long_horizon_ns else quality,
            )
            for h, p in zip(cfg.horizons_ns, predictions, strict=True)
        )
        sources = tuple(rows[i][0].identity for i in kept)
        return PredictedTrajectory(
            f"{e.entity_id.serial}:{domain.value}:{now}",
            e.entity_id,
            now,
            now,
            domain,
            frame,
            units,
            model,
            physical,
            position,
            velocity,
            "RESEARCH_METRIC_ESTIMATE" if domain == D.WORLD else "NON_PHYSICAL_RATE",
            samples,
            quality,
            tuple(reasons),
            sources,
            len(sources),
            sources[-1].observation_ns - sources[0].observation_ns,
            residual,
            rejected,
            tuple(
                dict.fromkeys(
                    (
                        self.provenance,
                        state.provenance,
                        *e.track_evidence.provenance,
                        *(
                            p
                            for h, _ in rows
                            for source in h.position_sources
                            for p in source.provenance
                        ),
                    )
                )
            ),
            self.hash,
        )
