"""Travel-direction evidence is distinct from optical-axis orientation."""

from dataclasses import dataclass
from math import isfinite, sqrt

from .contracts import ComponentProvenance, FrameIdentity
from .motion import CameraMotionEstimate


@dataclass(frozen=True)
class UserMotionHeadingEstimate:
    identity: FrameIdentity | None
    coordinate_frame: str
    direction: tuple[float, float, float] | None
    quality: str
    source: str
    age_ns: int | None
    uncertainty: str
    reasons: tuple[str, ...]
    provenance: ComponentProvenance


class UserMotionHeadingEstimator:
    def __init__(self, max_age_ns: int = 500_000_000) -> None:
        if type(max_age_ns) is not int or not 0 < max_age_ns <= 2_000_000_000:
            raise ValueError("Invalid heading freshness bound")
        self.max_age_ns = max_age_ns

    def estimate(
        self,
        motion: CameraMotionEstimate | None,
        now: FrameIdentity,
        camera_frame_id: str,
        *,
        rigid_mount_confirmed: bool = False,
        ground_normal_camera: tuple[float, float, float] | None = None,
    ) -> UserMotionHeadingEstimate:
        reasons = []
        age = None if motion is None else now.observation_ns - motion.pair.b.observation_ns
        if not rigid_mount_confirmed:
            reasons.append("CAMERA_MOTION_NOT_CONFIRMED_AS_USER_MOTION")
        if motion is None:
            reasons.append("TRANSLATION_EVIDENCE_UNAVAILABLE")
        elif (
            motion.pair.b.source_id != now.source_id
            or motion.pair.b.timing != now.timing
            or motion.pair.b.sequence > now.sequence
            or age is None
            or not 0 <= age < self.max_age_ns
            or motion.quality.state not in {"GOOD", "DEGRADED"}
            or motion.translation_direction is None
        ):
            reasons.append("TRANSLATION_EVIDENCE_UNUSABLE")
        if ground_normal_camera is None:
            reasons.append("GROUND_ORIENTATION_UNAVAILABLE")
        elif (
            len(ground_normal_camera) != 3
            or not all(isfinite(v) for v in ground_normal_camera)
            or abs(sum(v * v for v in ground_normal_camera) - 1) > 1e-6
        ):
            raise ValueError("Unit finite ground normal required")
        direction = None
        if not reasons:
            assert motion is not None and motion.translation_direction is not None
            assert ground_normal_camera is not None
            # X_B = R X_A + t: camera travel expressed in current camera B is -t.
            # This is neither camera-forward nor an absolute compass/body heading.
            travel = tuple(-float(v) for v in motion.translation_direction)
            vertical = sum(a * b for a, b in zip(travel, ground_normal_camera, strict=True))
            planar = tuple(
                a - vertical * b for a, b in zip(travel, ground_normal_camera, strict=True)
            )
            norm = sqrt(sum(v * v for v in planar))
            if norm < 0.1:
                reasons.append("GROUND_TRAVEL_DIRECTION_DEGENERATE")
            else:
                direction = (planar[0] / norm, planar[1] / norm, planar[2] / norm)
                reasons.append("RIGID_MOUNT_ASSUMPTION; VISUAL_DIRECTION_UNVALIDATED")
        return UserMotionHeadingEstimate(
            motion.pair.b if motion else None,
            camera_frame_id,
            direction,
            "DEGRADED" if direction is not None else "UNKNOWN",
            "VISUAL_CAMERA_TRANSLATION_PROJECTED_ON_SUPPLIED_GROUND"
            if direction
            else "UNAVAILABLE",
            age if age is not None and age >= 0 else None,
            "UNQUANTIFIED",
            tuple(reasons),
            ComponentProvenance("user-motion-heading-v1", "heading-estimator"),
        )
