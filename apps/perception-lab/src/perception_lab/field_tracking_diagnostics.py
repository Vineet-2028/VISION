"""Opt-in bounded observations of frozen association costs; never changes assignment."""

from math import hypot, isfinite
from typing import Any

from .detection import Detection
from .detection_metrics import iou
from .tracking import AssociationTracker
from .tracking_types import TrackSet


class DiagnosticTracker(AssociationTracker):
    diagnostic: dict[str, Any]

    def update(self, *args: Any, **kwargs: Any) -> TrackSet:
        self.diagnostic = {"cost_observations": [], "truncated": False}
        result = super().update(*args, **kwargs)
        self.diagnostic.update(
            source_id=result.identity.source_id,
            source_sequence=result.identity.sequence,
            source_observation_ns=str(result.identity.observation_ns),
            first_confirmed_failure_stage="UNKNOWN",
            unknown_evidence=["Physical identity of unassociated detections"],
            update_reasons=list(result.diagnostics),
            removed_track_generations=[track.serial for track in result.removed],
            track_outcomes=[
                {
                    "track_generation": track.track_id.serial,
                    "lifecycle": track.lifecycle.value,
                    "observation_status": track.observation_status,
                    "latest_observed_ns": str(track.latest_observed_ns),
                    "latest_failure": track.latest_failure,
                }
                for track in result.tracks[:16]
            ],
        )
        return result

    def _cost(self, track: Any, detection: Detection) -> float:
        cost = super()._cost(track, detection)
        observations = self.diagnostic["cost_observations"]
        if len(observations) >= 64:
            self.diagnostic["truncated"] = True
            return cost
        reason = "ELIGIBLE_COST_NOT_ASSIGNMENT"
        if not isfinite(cost):
            a, b = track.predicted, detection.box
            distance = hypot(
                (a.x1 + a.x2 - b.x1 - b.x2) / 2, (a.y1 + a.y2 - b.y1 - b.y2) / 2
            ) / max(1.0, hypot(a.x2 - a.x1, a.y2 - a.y1))
            if distance > self.config.center_gate:
                reason = "CENTER_DISTANCE_GATE"
            elif self.config.tracker_type == "iou" and iou(a, b) < self.config.min_iou:
                reason = "MINIMUM_IOU_GATE"
            else:
                reason = "NONOVERLAP_DISPLACEMENT_GATE"
        elif cost >= self.config.unmatched_cost:
            reason = "UNMATCHED_COST_GATE"
        observations.append(
            {
                "track_session": track.id.session_id,
                "track_generation": track.id.serial,
                "candidate_box": list(detection.box.coordinates),
                "candidate_score": detection.confidence,
                "cost": cost if isfinite(cost) else None,
                "reason": reason,
                "assignment": "NOT_INFERRED_FROM_COST",
            }
        )
        return cost
