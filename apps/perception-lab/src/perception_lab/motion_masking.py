"""Optional semantic exclusions. Unmasked features are candidates, not proven static."""

from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from .contracts import FrameIdentity
from .detection import Box, DetectionBatch, ObjectClass
from .flow import SparseFlowObservation
from .tracking_types import TrackSet


class SemanticExclusion(Protocol):
    def excluded(
        self, identity: FrameIdentity, points: NDArray[np.float64]
    ) -> NDArray[np.bool_]: ...


def dynamic_exclusions(
    flow: SparseFlowObservation,
    detections: DetectionBatch | None = None,
    tracks: TrackSet | None = None,
    semantic: SemanticExclusion | None = None,
) -> NDArray[np.bool_]:
    boxes: list[Box] = []
    if detections is not None:
        if detections.identity != flow.pair.b:
            raise ValueError("Detection mask frame mismatch")
        boxes.extend(
            d.box
            for d in detections.detections
            if d.entity_observation is not None or d.label != ObjectClass.UNKNOWN
        )
    if tracks is not None:
        if tracks.identity != flow.pair.b or tracks.session_id != flow.pair.session_id:
            raise ValueError("Track mask identity mismatch")
        boxes.extend(
            t.latest_observed_bbox
            for t in tracks.tracks
            if t.observation_status == "OBSERVED"
            and t.latest_observed_ns == flow.pair.b.observation_ns
            and (t.entity_observation is not None or t.category != ObjectClass.UNKNOWN)
        )
    mask = np.zeros(len(flow.valid), dtype=np.bool_)
    x, y = flow.points_b.T
    for box in boxes:
        mask |= (x >= box.x1) & (x < box.x2) & (y >= box.y1) & (y < box.y2)
    if semantic is not None:
        extra = semantic.excluded(flow.pair.b, flow.points_b)
        if extra.shape != mask.shape or extra.dtype != np.bool_:
            raise ValueError("Semantic mask mismatch")
        mask |= extra
    return mask
