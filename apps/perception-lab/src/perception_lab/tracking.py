"""Single-owner bounded tracking. No detector/runtime or physical-motion dependencies."""

from collections import deque
from dataclasses import dataclass
from math import hypot, inf
from threading import get_ident

from .config import canonical_hash
from .contracts import ComponentProvenance, FrameIdentity, TimingProvenance
from .detection import Box, Detection, DetectionBatch, ObjectClass
from .detection_metrics import iou
from .tracking_assignment import assign
from .tracking_config import TrackerConfig
from .tracking_motion import ImageMotion
from .tracking_types import (
    DetectorEvidence,
    Lifecycle,
    TrackId,
    TrackObservation,
    TrackSet,
    TrackSnapshot,
)


@dataclass
class _Track:
    id: TrackId
    motion: ImageMotion
    born: int
    observed: int
    latest_box: Box
    predicted: Box
    confidence: float
    provenance: ComponentProvenance
    history: deque[TrackObservation]
    votes: dict[ObjectClass, float]
    lifecycle: Lifecycle = Lifecycle.TENTATIVE
    confirmed: bool = False
    hits: int = 1
    misses: int = 0
    streak: int = 1
    miss_streak: int = 0
    association: float = 1.0
    failure_factor: float = 1.0
    latest_failure: str | None = None

    def category(self) -> ObjectClass:
        return min(self.votes, key=lambda c: (-self.votes[c], c.value))


class AssociationTracker:
    """IoU, motion and two-stage policies share the same stable output contract.

    Updates reject incompatible inputs before mutation. Reset is explicit. IDs
    remain monotonic even if reset reuses a session identifier. Instances are single-owner.
    """

    def __init__(
        self,
        config: TrackerConfig,
        session_id: str,
        source_id: str,
        width: int,
        height: int,
        *,
        objectness_first: bool = False,
    ) -> None:
        self.config = config
        self.objectness_first = objectness_first
        self.provenance = ComponentProvenance(
            "AssociationTracker/" + config.tracker_type,
            "tracker",
            "image-space-objectness-v02" if objectness_first else "image-space-v1",
            "1",
            "numpy",
            canonical_hash({**config.model_dump(), "objectness_first": True})
            if objectness_first
            else canonical_hash(config.model_dump()),
        )
        self._owner = get_ident()
        self._next_id = 1
        self._tracks: list[_Track] = []
        self.reset(session_id, source_id, width, height)

    def _check_owner(self) -> None:
        if get_ident() != self._owner:
            raise ValueError("Tracker requires single-writer ownership")

    def reset(self, session_id: str, source_id: str, width: int, height: int) -> None:
        self._check_owner()
        if not session_id or not source_id or not 0 < width <= 100000 or not 0 < height <= 100000:
            raise ValueError("Invalid tracker session/dimensions")
        self.session_id, self.source_id = session_id, source_id
        self.width, self.height = width, height
        self._tracks.clear()
        self._last: FrameIdentity | None = None
        self._closed = False

    def close(self) -> None:
        self._check_owner()
        self._tracks.clear()
        self._closed = True

    def _cost(self, track: _Track, detection: Detection) -> float:
        # Prediction was already validated once per track at this update's time.
        # Reconstructing/validating it for every candidate makes the bounded
        # association matrix needlessly dominated by NumPy scalar reductions.
        a, b = track.predicted, detection.box
        overlap = iou(a, b)
        distance = hypot((a.x1 + a.x2 - b.x1 - b.x2) / 2, (a.y1 + a.y2 - b.y1 - b.y2) / 2) / max(
            1.0, hypot(a.x2 - a.x1, a.y2 - a.y1)
        )
        if distance > self.config.center_gate:
            return inf
        if self.config.tracker_type == "iou" and overlap < self.config.min_iou:
            return inf
        # Motion policies can bridge non-overlap only within half the displacement gate.
        if overlap < self.config.min_iou and distance > self.config.center_gate / 2:
            return inf
        penalty = (
            self.config.class_penalty
            if not self.objectness_first and track.category() != detection.label
            else 0.0
        )
        return 1 - overlap + self.config.center_weight * distance + penalty

    def update(
        self,
        session_id: str,
        identity: FrameIdentity,
        evidence: DetectorEvidence,
        batch: DetectionBatch | None = None,
        failure_code: str | None = None,
    ) -> TrackSet:
        self._check_owner()
        if (
            self._closed
            or session_id != self.session_id
            or identity.source_id != self.source_id
            or identity.timing == TimingProvenance.UNKNOWN
        ):
            raise ValueError("Tracker temporal identity mismatch or closed session")
        if self._last is not None and (
            identity.observation_ns <= self._last.observation_ns
            or identity.sequence <= self._last.sequence
            or identity.timing != self._last.timing
            or identity.observation_ns - self._last.observation_ns > self.config.max_step_ns
        ):
            raise ValueError("Timestamp/sequence discontinuity requires explicit reset")
        success = evidence in (DetectorEvidence.SUCCESS, DetectorEvidence.SUCCESS_EMPTY)
        if (
            not isinstance(evidence, DetectorEvidence)
            or success != (batch is not None)
            or (batch is not None and batch.identity != identity)
            or (
                batch is not None
                and (not batch.detections) != (evidence == DetectorEvidence.SUCCESS_EMPTY)
            )
            or (evidence == DetectorEvidence.FAILURE) != (failure_code is not None)
        ):
            raise ValueError("Inconsistent detector evidence")
        # Never retain arbitrary exception text/private paths in provenance.
        if failure_code is not None and failure_code not in {"INFERENCE_FAILURE", "UNAVAILABLE"}:
            raise ValueError("Unsupported public failure code")
        detections = batch.detections if batch is not None else ()
        if any(
            d.entity_observation is not None
            and (not self.objectness_first or d.entity_observation.source_frame != identity)
            for d in detections
        ):
            raise ValueError(
                "Generic observations require objectness mode and exact frame identity"
            )
        if len(detections) > 10000:
            raise ValueError("Input exceeds defensive detection limit")
        if any(d.box.area <= 0 or max(abs(v) for v in d.box.coordinates) > 1e7 for d in detections):
            raise ValueError("Invalid tracking box")
        now = identity.observation_ns
        dt = (now - self._last.observation_ns) / 1e9 if self._last else 0.0
        diagnostics: list[str] = []
        removed: list[TrackId] = []
        retained = []
        for track in self._tracks:
            expired = now - track.observed > self.config.max_unobserved_ns
            expired |= not track.confirmed and now - track.born > self.config.confirmation_window_ns
            try:
                if not expired:
                    track.predicted = track.motion.predict(dt)
            except ValueError:
                expired = True
                diagnostics.append("INVALID_PREDICTION_REMOVED")
            if expired:
                removed.append(track.id)
            else:
                retained.append(track)
        self._tracks = retained
        ordered = sorted(
            (
                d
                for d in detections
                if (self.objectness_first or d.label != ObjectClass.UNKNOWN) and d.confidence > 0
            ),
            key=lambda d: (
                -d.confidence,
                "" if self.objectness_first else d.label.value,
                d.box.coordinates,
            ),
        )
        if len(ordered) > self.config.max_detections:
            diagnostics.append("DETECTION_CAP_REACHED")
        filtered: list[Detection] = []
        for detection in ordered[: self.config.max_detections]:
            if any(
                (self.objectness_first or d.label == detection.label)
                and iou(d.box, detection.box) >= self.config.duplicate_iou
                for d in filtered
            ):
                diagnostics.append("DUPLICATE_DETECTION_SUPPRESSED")
            else:
                filtered.append(detection)
        high = [
            i for i, d in enumerate(filtered) if d.confidence >= self.config.publication_threshold
        ]
        low = [
            i
            for i, d in enumerate(filtered)
            if self.config.recovery_threshold <= d.confidence < self.config.publication_threshold
        ]
        matches: list[tuple[int, int]] = []
        available = list(range(len(self._tracks)))
        for candidates in (high, low if self.config.tracker_type == "two_stage" else []):
            rows = (
                available
                if candidates is high
                else [i for i in available if self._tracks[i].confirmed]
            )
            if not rows or not candidates:
                continue
            costs = [[self._cost(self._tracks[i], filtered[j]) for j in candidates] for i in rows]
            stage = [(rows[i], candidates[j]) for i, j in assign(costs, self.config.unmatched_cost)]
            matches.extend(stage)
            matched_rows = {i for i, _ in stage}
            available = [i for i in available if i not in matched_rows]
        for i, j in matches:
            track, detection = self._tracks[i], filtered[j]
            cost = self._cost(track, detection)
            track.association = max(0.0, 1 - cost / self.config.unmatched_cost)
            track.motion.correct(detection.box, (now - track.observed) / 1e9, track.latest_box)
            track.latest_box, track.observed = detection.box, now
            track.confidence = detection.confidence
            assert batch is not None
            track.provenance = batch.provenance
            track.failure_factor, track.latest_failure = 1.0, None
            track.hits += 1
            track.streak += 1
            track.miss_streak = 0
            if track.streak >= self.config.minimum_hits:
                track.confirmed = True
            track.lifecycle = Lifecycle.CONFIRMED if track.confirmed else Lifecycle.TENTATIVE
            for label in track.votes:
                track.votes[label] *= self.config.category_decay
            track.votes[detection.label] = (
                track.votes.get(detection.label, 0) + detection.confidence
            )
            track.history.append(
                TrackObservation(
                    identity,
                    detection.box,
                    detection.label,
                    detection.confidence,
                    track.association,
                    batch.provenance,
                    entity_observation=detection.entity_observation,
                )
            )
        for i in available:
            track = self._tracks[i]
            if success:
                track.misses += 1
                track.miss_streak += 1
                track.streak = 0
                if track.confirmed:
                    track.lifecycle = Lifecycle.LOST
            elif evidence in (DetectorEvidence.FAILURE, DetectorEvidence.UNAVAILABLE):
                track.failure_factor *= self.config.failure_quality_factor
                track.latest_failure = failure_code or "UNAVAILABLE"
        used = {j for _, j in matches}
        for j in high:
            if j in used:
                continue
            detection = filtered[j]
            if any(
                (self.objectness_first or t.category() == detection.label)
                and iou(t.motion.box(), detection.box) >= self.config.duplicate_iou
                for t in self._tracks
            ):
                diagnostics.append("DUPLICATE_BIRTH_SUPPRESSED")
                continue
            if len(self._tracks) >= self.config.max_tracks:
                diagnostics.append("TRACK_CAP_REACHED")
                break
            assert batch is not None
            observation = TrackObservation(
                identity,
                detection.box,
                detection.label,
                detection.confidence,
                1.0,
                batch.provenance,
                entity_observation=detection.entity_observation,
            )
            self._tracks.append(
                _Track(
                    TrackId(self.session_id, self._next_id),
                    ImageMotion(detection.box, self.config),
                    now,
                    now,
                    detection.box,
                    detection.box,
                    detection.confidence,
                    batch.provenance,
                    deque([observation], maxlen=self.config.history_capacity),
                    {detection.label: detection.confidence},
                )
            )
            self._next_id += 1
        self._last = identity
        snapshots = []
        for track in self._tracks:
            age = now - track.observed
            recency = max(0.0, 1 - age / self.config.max_unobserved_ns)
            quality = track.confidence * track.association * recency * track.failure_factor
            snapshots.append(
                TrackSnapshot(
                    track.id,
                    track.lifecycle,
                    "OBSERVED" if age == 0 else "PREDICTED",
                    track.category(),
                    track.votes[track.category()] / sum(track.votes.values()),
                    track.motion.box(),
                    track.predicted,
                    track.latest_box,
                    track.observed,
                    now,
                    now - track.born,
                    age,
                    track.hits,
                    track.misses,
                    track.streak,
                    track.miss_streak,
                    track.confidence,
                    quality,
                    tuple(map(float, track.motion.velocity)),
                    float(track.motion.covariance[:, 0, 0].sum()),
                    tuple(track.history),
                    track.provenance,
                    track.latest_failure,
                    entity_observation=track.history[-1].entity_observation,
                )
            )
        return TrackSet(
            self.session_id,
            identity,
            tuple(snapshots),
            tuple(removed),
            evidence,
            tuple(sorted(set(diagnostics))),
            self.provenance,
        )
