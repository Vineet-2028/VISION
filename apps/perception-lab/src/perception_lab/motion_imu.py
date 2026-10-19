"""Timestamp-aligned rotation only. No latest-sample substitution or blind fusion."""

from time import perf_counter_ns

import numpy as np
from numpy.typing import NDArray

from .contracts import ComponentProvenance
from .flow import SparseFlowObservation
from .geometry import MotionPoseHistory
from .motion import CameraMotionEstimate, MotionQuality, ScaleStatus
from .motion_geometry import require_calibration


class ImuRotationEstimator:
    def __init__(self, history: MotionPoseHistory, provenance: ComponentProvenance) -> None:
        self.history, self.provenance = history, provenance

    def estimate(
        self, flow: SparseFlowObservation, excluded: NDArray[np.bool_] | None = None
    ) -> CameraMotionEstimate:
        start = perf_counter_ns()
        require_calibration(self.history.g, flow.pair)
        rotation = self.history.relative_rotation(flow.pair.session_id, flow.pair.a, flow.pair.b)
        quality = MotionQuality(
            "DEGRADED" if rotation is not None else "UNAVAILABLE",
            "TIMESTAMP_ALIGNED_ROTATION" if rotation is not None else "IMU_UNAVAILABLE",
            0,
            0,
            0,
            0,
            calibration_quality=self.history.g.c.calibration_quality.state,
        )
        return CameraMotionEstimate(
            flow.pair,
            rotation,
            None,
            ScaleStatus.NONE,
            quality,
            self.provenance,
            start,
            perf_counter_ns(),
        )


def rotation_disagreement(a: CameraMotionEstimate, b: CameraMotionEstimate) -> float | None:
    if a.pair != b.pair:
        raise ValueError("Rotation comparison requires identical pair")
    if a.rotation is None or b.rotation is None:
        return None
    return float(np.arccos(np.clip((np.trace(a.rotation @ b.rotation.T) - 1) / 2, -1, 1)))
