"""Validity policy around authoritative Guardian math, not a second TTC/CPA implementation."""

from math import isfinite

from .contracts import ComponentProvenance
from .depth import DepthKind
from .geometry import CoreGeometry
from .interaction_config import InteractionConfig
from .interaction_types import (
    ClosestApproachCandidate,
    InteractionLevel,
    ReferenceMotion,
    TimeToContactCandidate,
)
from .trajectory_types import PredictedTrajectory, TrajectoryDomain, TrajectoryPhysicalStatus
from .world_types import EvidenceStatus, WorldEntity, WorldState


def candidates(
    t: PredictedTrajectory,
    e: WorldEntity,
    state: WorldState,
    horizon_ns: int,
    config: InteractionConfig,
    geometry: CoreGeometry | None,
    reference: ReferenceMotion | None,
    level: InteractionLevel,
    quality: str,
    calibration_id: str | None,
) -> tuple[TimeToContactCandidate, ClosestApproachCandidate]:
    status = "UNVALIDATED_PHYSICAL_INPUT"
    assumptions: tuple[str, ...] = (
        "USER_VELOCITY_UNAVAILABLE",
        "RESEARCH_ONLY",
        "LINEAR_RELATIVE_MOTION",
    )
    source = t.trajectory_id
    provenance = (*t.provenance, ComponentProvenance("Guardian.Motion", "relative-motion"))
    ref_type = reference.reference_type if reference else "UNAVAILABLE_USER_REFERENCE"
    values = None
    if t.coordinate_space != TrajectoryDomain.WORLD or t.units != "meters":
        status = "INVALID_UNITS"
    elif t.physical_status != TrajectoryPhysicalStatus.WORLD_RESEARCH_UNVALIDATED:
        # Future validation needs an evidence authority, not a string promotion.
        status = "UNSUPPORTED_PHYSICAL_VALIDATION_AUTHORITY"
    elif not config.research_metric:
        status = "RESEARCH_METRIC_DISABLED"
    elif geometry is None:
        status = "GUARDIAN_UNAVAILABLE"
    elif (
        quality == "UNAVAILABLE"
        or t.quality in {"UNAVAILABLE", "UNRELIABLE"}
        or t.velocity_status != "RESEARCH_METRIC_ESTIMATE"
        or e.observation_status != "OBSERVED"
    ):
        status = "INSUFFICIENT_VELOCITY"
    elif (
        e.depth is None
        or e.track_evidence.identity is None
        or e.depth.representation.kind != DepthKind.METRIC
        or e.position_world is None
        or e.position_world.world_frame_id != t.frame_id
        or e.position_world.identity != e.track_evidence.identity
        or e.depth.identity != e.track_evidence.identity
        or e.depth_evidence.identity != e.track_evidence.identity
        or state.state_timestamp - e.depth.identity.observation_ns > config.max_age_ns
        or e.position_world.camera_point.depth.representation.kind != DepthKind.METRIC
        or e.position_world.camera_point.identity != e.track_evidence.identity
        or state.camera_state.calibration_quality not in {"VALID", "DEGRADED"}
        or state.camera_state.calibration_id != calibration_id
        or e.depth_evidence.status not in {EvidenceStatus.FRESH, EvidenceStatus.DEGRADED}
        or e.depth_evidence.quality in {"UNAVAILABLE", "UNRELIABLE"}
        or state.camera_state.pose is None
        or state.camera_state.pose.identity.observation_ns != state.state_timestamp
        or state.camera_state.pose.world_frame_id != t.frame_id
        or state.camera_state.pose_evidence.status != EvidenceStatus.FRESH
        or state.camera_state.pose_evidence.identity != state.camera_state.pose.identity
        or state.camera_state.pose.identity.source_id != e.track_evidence.identity.source_id
    ):
        status = "INSUFFICIENT_POSITION"
    else:
        if reference is None and config.static_user_reference:
            pose = state.camera_state.pose
            reference = ReferenceMotion(
                state.session_id,
                state.state_timestamp,
                t.frame_id,
                pose.translation_meters,
                (0.0, 0.0, 0.0),
                "STATIC_USER_CURRENT_ORIGIN_REFERENCE",
                "UNVALIDATED",
                "DEGRADED",
                state.camera_state.pose_evidence.provenance,
            )
        if reference is None:
            status = "USER_VELOCITY_UNAVAILABLE"
        else:
            ref_type = reference.reference_type
            if ref_type == "STATIC_USER_CURRENT_ORIGIN_REFERENCE" and (
                not config.static_user_reference or any(reference.velocity)
            ):
                raise ValueError("Static-user research reference must be enabled and stationary")
            if (
                reference.session_id != state.session_id
                or reference.state_timestamp != state.state_timestamp
                or reference.frame_id != t.frame_id
                or reference.units != "meters"
                or reference.velocity_units != "meters/second"
                or reference.quality not in {"GOOD", "DEGRADED"}
                or len(reference.position) != 3
                or len(reference.velocity) != 3
                or any(
                    not isfinite(v) or abs(v) > 1e9
                    for v in (*reference.position, *reference.velocity)
                )
            ):
                raise ValueError("Incompatible relative-motion reference")
            assumptions = (
                "RESEARCH_ONLY",
                "METRIC_DEPTH_UNVALIDATED",
                "LINEAR_RELATIVE_MOTION",
                "STATIC_USER_ASSUMPTION"
                if ref_type == "STATIC_USER_CURRENT_ORIGIN_REFERENCE"
                else "SUPPLIED_REFERENCE_MOTION_NOT_PHYSICAL_VALIDATION",
            )
            provenance = (*provenance, *reference.provenance)
            values = geometry.relative_motion(
                t.frame_id, t.origin, t.velocity, reference.position, reference.velocity
            )
            status = "COMPUTABLE_RESEARCH"
    ttc_status = cpa_status = status
    if values is not None:
        if values.closing_speed_mps is None:
            ttc_status = "ZERO_OR_NEAR_ZERO_DISTANCE"
        elif values.closing_speed_mps <= config.minimum_closing_speed_mps:
            ttc_status = "NON_CLOSING"
        elif values.ttc_seconds is None:
            ttc_status = "UNAVAILABLE"
        elif values.ttc_seconds > horizon_ns / 1e9:
            ttc_status = "OUTSIDE_PREDICTION_HORIZON"
        if values.stationary:
            cpa_status = "ZERO_RELATIVE_VELOCITY"
        elif values.cpa_seconds is None:
            cpa_status = "UNAVAILABLE"
        elif values.cpa_seconds < 0:
            cpa_status = "PAST_CLOSEST_APPROACH"
        elif values.cpa_seconds > horizon_ns / 1e9:
            cpa_status = "OUTSIDE_PREDICTION_HORIZON"
    return (
        TimeToContactCandidate(
            ttc_status,
            values.ttc_seconds
            if values and ttc_status in {"COMPUTABLE_RESEARCH", "OUTSIDE_PREDICTION_HORIZON"}
            else None,
            values.closing_speed_mps if values else None,
            ref_type,
            level,
            quality,
            source,
            source + " relative to " + ref_type,
            assumptions,
            provenance,
        ),
        ClosestApproachCandidate(
            cpa_status,
            values.cpa_seconds if values else None,
            values.cpa_distance_meters if values else None,
            values.separation_meters if values else None,
            ref_type,
            level,
            quality,
            source,
            source + " relative to " + ref_type,
            assumptions,
            provenance,
        ),
    )
