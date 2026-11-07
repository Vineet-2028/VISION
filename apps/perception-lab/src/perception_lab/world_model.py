"""Single-writer, bounded, conservative fusion of Sentinel observation contracts."""

from collections import deque
from dataclasses import dataclass, replace
from math import isfinite
from threading import get_ident

import numpy as np

from .config import canonical_hash
from .contracts import ComponentProvenance, FrameIdentity, FrameResult, TimingProvenance
from .depth import DepthKind
from .depth_sampling import TrackDepthObservation
from .depth_spatial import CameraPointEstimate, SuppliedDepthPose, camera_point, world_point
from .detection import DetectionBatch
from .geometry import CoreGeometry
from .motion import CameraMotionEstimate, ScaleStatus, TrackImageMotionObservation
from .perceived_entity import PerceivedEntityObservation
from .semantics import SemanticClass as C
from .semantics import SemanticFrame
from .surfaces import SurfaceEvidenceFrame, SurfaceFlag
from .track_semantics import SemanticFusionConfig, TrackSemanticFusion
from .tracking_types import DetectorEvidence, Lifecycle, TrackId, TrackSet, TrackSnapshot
from .world_config import WorldModelConfig
from .world_types import (
    Capability,
    EntityHistory,
    EntityLifecycle,
    EvidenceSource,
    SurfaceGroundCandidate,
    WorldCameraState,
    WorldEntity,
    WorldEntityId,
    WorldImageGeometry,
    WorldSceneQuality,
    WorldState,
    WorldSurfaceState,
)
from .world_types import (
    EvidenceStatus as S,
)

SOURCES = ("camera", "detector", "tracking", "depth", "motion", "pose", "semantics", "surface")


def surface_samples(surface: SurfaceEvidenceFrame) -> tuple[tuple[float, float, int], ...]:
    """At most 768 center samples; no dense copy or area-coverage claim."""
    height, width = surface.evidence.shape
    xs = ((np.arange(min(width, 32)) + 0.5) * width / min(width, 32)).astype(int)
    ys = ((np.arange(min(height, 24)) + 0.5) * height / min(height, 24)).astype(int)
    values = surface.evidence[np.ix_(ys, xs)]
    return tuple(
        (float(x) + 0.5, float(y) + 0.5, int(v))
        for y, row in zip(ys, values, strict=True)
        for x, v in zip(xs, row, strict=True)
    )


@dataclass
class _Entity:
    entity_id: WorldEntityId
    track: TrackSnapshot
    identity: FrameIdentity
    provenance: ComponentProvenance
    history: deque[EntityHistory]
    depth: TrackDepthObservation | None = None
    point: CameraPointEstimate | None = None
    motion: TrackImageMotionObservation | None = None
    motion_provenance: tuple[ComponentProvenance, ...] = ()
    semantic_evidence: EvidenceSource | None = None
    semantic_label: str | None = None
    concept_fusion: TrackSemanticFusion | None = None


class PrototypeWorldModel:
    def __init__(
        self,
        config: WorldModelConfig,
        session_id: str,
        source_id: str,
        geometry: CoreGeometry | None = None,
    ) -> None:
        self.config, self.geometry = config, geometry
        self.provenance = ComponentProvenance(
            "PrototypeWorldModel",
            "world_model",
            "conservative-evidence-v1",
            "1",
            "python",
            canonical_hash(config.model_dump()),
        )
        self._owner = get_ident()
        self._calibration_id = (
            canonical_hash(geometry.c.model_dump(exclude={"metadata"})) if geometry else None
        )
        self._serial = 0
        self.reset(session_id, source_id)

    def _owner_check(self) -> None:
        if get_ident() != self._owner:
            raise ValueError("World model requires single-writer ownership")

    def reset(self, session_id: str, source_id: str) -> None:
        self._owner_check()
        if not session_id or not source_id:
            raise ValueError("Explicit session/source required")
        self.session_id, self.source_id = session_id, source_id
        self._time = -1
        self._timing: TimingProvenance | None = None
        self._closed = False
        self._entities: dict[TrackId, _Entity] = {}
        self._sources: dict[str, EvidenceSource] = {}
        self._watermarks: dict[str, FrameIdentity] = {}
        self._diagnostics: deque[str] = deque(maxlen=self.config.diagnostic_count)
        self._surface: WorldSurfaceState | None = None
        self._semantic_counts: tuple[tuple[str, int], ...] = ()
        self._pose: SuppliedDepthPose | None = None
        self._motion: CameraMotionEstimate | None = None
        self._pose_source: EvidenceSource | None = None
        self._motion_source: EvidenceSource | None = None
        self.created = self.expired = self.peak_entities = self.snapshots = 0

    def close(self) -> None:
        self._owner_check()
        self._entities.clear()
        self._sources.clear()
        self._watermarks.clear()
        self._diagnostics.clear()
        self._surface = self._pose = self._motion = None
        self._semantic_counts = ()
        self._pose_source = self._motion_source = None
        self._closed = True

    def _validate(self, session: str, identity: FrameIdentity, now: int) -> None:
        self._owner_check()
        if self._closed or session != self.session_id or identity.source_id != self.source_id:
            raise ValueError("World session/source mismatch or closed")
        if (
            identity.timing == TimingProvenance.UNKNOWN
            or self._timing is not None
            and identity.timing != self._timing
            or not 0 <= now <= 2**63 - 1
            or now < self._time
            or identity.observation_ns > now
        ):
            raise ValueError("World clock reversal, unknown clock or future observation")

    def _accept(self, source: str, session: str, identity: FrameIdentity, now: int) -> bool:
        self._validate(session, identity, now)
        previous = self._watermarks.get(source)
        if now - identity.observation_ns > self.config.late_ns:
            self._diagnostics.append(source.upper() + "_LATE_REJECTED")
            return False
        if previous is not None and (
            identity.observation_ns <= previous.observation_ns
            or identity.sequence <= previous.sequence
        ):
            self._diagnostics.append(source.upper() + "_DUPLICATE_OR_OLDER_REJECTED")
            return False
        self._timing = identity.timing
        self._time = now
        self._watermarks[source] = identity
        return True

    def _source(
        self,
        name: str,
        identity: FrameIdentity,
        provenance: tuple[ComponentProvenance, ...],
        observation: str = "OBSERVED",
        quality: str = "UNCALIBRATED",
        validation: str = "UNVALIDATED",
        status: S = S.FRESH,
        reason: str | None = None,
    ) -> EvidenceSource:
        value = EvidenceSource(
            name, identity, 0, status, observation, quality, validation, provenance, reason
        )
        previous = self._sources.get(name)
        if (
            previous is None
            or previous.identity is None
            or previous.identity.observation_ns <= identity.observation_ns
        ):
            self._sources[name] = value
        return value

    def _age(self, value: EvidenceSource, now: int, force_stale: bool = False) -> EvidenceSource:
        if value.identity is None:
            return value
        age = now - value.identity.observation_ns
        window = (
            self.config.semantic_fresh_ns
            if value.subsystem in {"surface", "semantics"}
            else self.config.fresh_ns
        )
        status = value.status
        if status not in {S.UNAVAILABLE, S.FAILED, S.UNRELIABLE} and (age > window or force_stale):
            status = S.STALE
        return replace(value, age_ns=age, status=status)

    def _get(self, name: str, now: int) -> EvidenceSource:
        value = self._sources.get(
            name,
            EvidenceSource(
                name,
                None,
                None,
                S.UNAVAILABLE,
                "UNAVAILABLE",
                "UNKNOWN",
                "UNVALIDATED",
                reason=name.upper() + "_UNAVAILABLE",
            ),
        )
        return self._age(value, now)

    def _payload_source(
        self, name: str, original: EvidenceSource | None, now: int
    ) -> EvidenceSource:
        if original is None:
            return self._get(name, now)
        value = self._age(original, now)
        if self._get(name, now).status == S.FAILED:
            value = replace(value, status=S.FAILED, reason="SOURCE_FAILURE")
        return value

    def ingest_tracks(self, tracks: TrackSet, now: int) -> None:
        self._validate(tracks.session_id, tracks.identity, now)
        ids = [t.track_id for t in tracks.tracks]
        if len(ids) != len(set(ids)) or len(ids) > 10000:
            raise ValueError("Duplicate tracks or excessive input")
        for t in tracks.tracks:
            if t.entity_observation is not None and (
                t.entity_observation.source_frame.source_id != tracks.identity.source_id
                or t.entity_observation.source_frame.timing != tracks.identity.timing
                or t.entity_observation.source_frame.observation_ns != t.latest_observed_ns
                or t.entity_observation.bbox != t.latest_observed_bbox
            ):
                raise ValueError("Generic track evidence has mismatched source/time/geometry")
            if (
                t.track_id.session_id != self.session_id
                or t.state_ns != tracks.identity.observation_ns
                or not 0 <= t.latest_observed_ns <= t.state_ns
                or t.observation_status not in {"OBSERVED", "PREDICTED"}
                or t.observation_status == "OBSERVED"
                and t.latest_observed_ns != t.state_ns
                or not 0 <= t.quality <= 1
                or not 0 <= t.category_confidence <= 1
            ):
                raise ValueError("Invalid track identity/status/time/quality")
        if any(t.session_id != self.session_id for t in tracks.removed):
            raise ValueError("Wrong-session removal")
        if not self._accept("tracking", tracks.session_id, tracks.identity, now):
            return
        self._prune(now)
        for track_id in tracks.removed:
            if self._entities.pop(track_id, None) is not None:
                self.expired += 1
        ordered = sorted(
            tracks.tracks, key=lambda t: (t.track_id not in self._entities, t.track_id)
        )
        for t in ordered:
            if t.lifecycle == Lifecycle.REMOVED:
                continue
            entry = self._entities.get(t.track_id)
            if entry is None:
                if len(self._entities) >= self.config.max_entities:
                    self._diagnostics.append("ENTITY_CAP_REACHED")
                    continue
                self._serial += 1
                entry = _Entity(
                    WorldEntityId(self.session_id, self._serial),
                    replace(t, history=()),
                    tracks.identity,
                    tracks.provenance,
                    deque(maxlen=self.config.history_count),
                )
                self._entities[t.track_id] = entry
                self.created += 1
            elif entry.track.category != t.category:
                self._diagnostics.append("TRACK_CATEGORY_CHANGED")
            if t.latest_observed_ns < entry.track.latest_observed_ns:
                self._diagnostics.append("TRACK_OBSERVATION_REGRESSION_REJECTED")
                continue
            entry.track, entry.identity, entry.provenance = (
                replace(t, history=()),
                tracks.identity,
                tracks.provenance,
            )
            if t.entity_observation is not None and t.observation_status == "OBSERVED":
                if entry.concept_fusion is None:
                    entry.concept_fusion = TrackSemanticFusion(
                        t.track_id, t.entity_observation.source_frame, SemanticFusionConfig()
                    )
                entry.concept_fusion.observe(t.entity_observation, now)
            if self.geometry and t.bearing_radians is None:
                angles = self.geometry.bearing_angles(
                    (t.bbox.x1 + t.bbox.x2) / 2, (t.bbox.y1 + t.bbox.y2) / 2, tracks.identity
                )
                entry.track = replace(entry.track, bearing_radians=angles)
            entry.history.append(
                EntityHistory(
                    tracks.identity,
                    t.bbox,
                    t.category,
                    t.observation_status,
                    t.quality,
                    bearing_radians=entry.track.bearing_radians,
                    calibration_id=self._calibration_id,
                )
            )
        self.peak_entities = max(self.peak_entities, len(self._entities))
        self._source(
            "tracking",
            tracks.identity,
            (tracks.provenance,),
            status=S.PREDICTED
            if tracks.tracks and all(t.observation_status == "PREDICTED" for t in tracks.tracks)
            else S.FRESH,
        )
        # NO_RUN is a tick outcome, not a fresh detector observation.
        if tracks.detector_evidence == DetectorEvidence.FAILURE:
            self.failure("detector", self.session_id, tracks.identity, now)
        elif tracks.detector_evidence == DetectorEvidence.UNAVAILABLE:
            self._source(
                "detector", tracks.identity, (), status=S.UNAVAILABLE, reason="DETECTOR_UNAVAILABLE"
            )
        elif tracks.detector_evidence == DetectorEvidence.NO_DETECTOR_RUN:
            self._diagnostics.append("NO_DETECTOR_RUN")

    def ingest_entity_semantics(
        self,
        entity_id: WorldEntityId,
        track_id: TrackId,
        observation: PerceivedEntityObservation,
        now: int,
    ) -> bool:
        self._validate(entity_id.session_id, observation.source_frame, now)
        entry = self._entities.get(track_id)
        if (
            entry is None
            or entry.entity_id != entity_id
            or entry.concept_fusion is None
            or entry.track.lifecycle == Lifecycle.LOST
            or entry.track.latest_observed_ns < observation.source_frame.observation_ns
            or not any(
                h.identity == observation.source_frame and h.observation_status == "OBSERVED"
                for h in entry.history
            )
        ):
            self._diagnostics.append("ENTITY_SEMANTICS_ASSOCIATION_REJECTED")
            return False
        try:
            entry.concept_fusion.observe(observation, now)
        except ValueError:
            self._diagnostics.append("ENTITY_SEMANTICS_STALE_OR_DUPLICATE_REJECTED")
            return False
        return True

    def ingest_detection(self, session: str, batch: DetectionBatch, now: int) -> None:
        if self._accept("detector", session, batch.identity, now):
            self._source(
                "detector",
                batch.identity,
                (batch.provenance,),
                observation="SUCCESS" if batch.detections else "SUCCESS_EMPTY",
            )

    def ingest_depth(self, observation: TrackDepthObservation, now: int) -> None:
        self._validate(observation.track_id.session_id, observation.identity, now)
        entry = self._entities.get(observation.track_id)
        estimate = observation.estimate
        if estimate is None:
            return
        if (
            estimate.identity != observation.identity
            or observation.depth_age_ns != 0
            or observation.observation_status != "EXACT_FRAME"
        ):
            raise ValueError("Depth association is not exact")
        if (
            entry is None
            or entry.identity != observation.identity
            or entry.track.observation_status != "OBSERVED"
        ):
            self._diagnostics.append("DEPTH_TRACK_FRAME_MISMATCH")
            return
        if now - observation.identity.observation_ns > self.config.late_ns:
            self._diagnostics.append("DEPTH_LATE_REJECTED")
            return
        if (
            entry.depth is not None
            and entry.depth.identity.observation_ns >= observation.identity.observation_ns
        ):
            self._diagnostics.append("DEPTH_DUPLICATE_OR_OLDER_REJECTED")
            return
        # Compute before mutation; Guardian remains authoritative for all geometry.
        point = (
            camera_point(estimate, self.geometry)
            if self.geometry and self.geometry.c.calibration_quality.state in {"VALID", "DEGRADED"}
            else None
        )
        entry.depth, entry.point = observation, point
        self._time = now
        if entry.history and entry.history[-1].identity == estimate.identity:
            entry.history[-1] = replace(
                entry.history[-1],
                depth_value=estimate.value,
                depth_kind=estimate.representation.kind.value,
                camera_point_meters=point.position_meters if point else None,
            )
        self._source(
            "depth",
            estimate.identity,
            (estimate.provenance,),
            quality=estimate.quality,
            validation="METRIC_DEPTH_UNVALIDATED"
            if estimate.representation.kind == DepthKind.METRIC
            else "RELATIVE_ONLY",
        )
        self._capture_world_history(entry, now)

    def _capture_world_history(self, entry: _Entity, now: int) -> None:
        """Retain only exact observed depth/pose joins, never a latest-pose substitution."""
        point, pose = entry.point, self._pose
        if (
            point is None
            or pose is None
            or self.geometry is None
            or not entry.history
            or entry.track.observation_status != "OBSERVED"
            or point.identity != pose.identity
            or point.identity != entry.history[-1].identity
            or self._get("pose", now).status != S.FRESH
        ):
            return
        wp = world_point(point, self.geometry, pose)
        if wp is not None:
            entry.history[-1] = replace(
                entry.history[-1],
                world_point=wp,
                position_sources=(self._get("depth", now), self._get("pose", now)),
            )

    def ingest_pose(
        self,
        session: str,
        pose: SuppliedDepthPose,
        provenance: ComponentProvenance,
        now: int,
        quality: str = "MODEL_ESTIMATE",
    ) -> None:
        if (
            quality not in {"MODEL_ESTIMATE", "SYNTHETIC", "UNRELIABLE"}
            or not all(isfinite(v) for v in (*pose.translation_meters, *pose.rotation_wxyz))
            or abs(sum(v * v for v in pose.rotation_wxyz) - 1) > 1e-6
            or not pose.world_frame_id
            or not pose.device_frame_id
        ):
            raise ValueError("Invalid pose")
        if (
            self.geometry
            and self.geometry.c.camera_to_device
            and pose.device_frame_id != self.geometry.c.camera_to_device.device_frame_id
        ):
            raise ValueError("Pose device frame mismatch")
        if self._accept("pose", session, pose.identity, now):
            self._pose = pose
            self._source(
                "pose",
                pose.identity,
                (provenance,),
                quality=quality,
                status=S.UNRELIABLE if quality == "UNRELIABLE" else S.FRESH,
            )
            self._pose_source = self._sources["pose"]
            for entry in self._entities.values():
                self._capture_world_history(entry, now)

    def ingest_camera_motion(self, motion: CameraMotionEstimate, now: int) -> None:
        if self._accept("motion", motion.pair.session_id, motion.pair.b, now):
            self._motion = motion
            self._source(
                "motion",
                motion.pair.b,
                (motion.provenance,),
                quality=motion.quality.state,
                status=S.UNAVAILABLE
                if motion.rotation is None
                else S.UNRELIABLE
                if motion.quality.state == "UNRELIABLE"
                else S.DEGRADED,
                reason=motion.quality.reason,
            )
            self._motion_source = self._sources["motion"]

    def ingest_image_motion(
        self,
        motion: TrackImageMotionObservation,
        provenance: tuple[ComponentProvenance, ...],
        now: int,
    ) -> None:
        self._validate(motion.track_id.session_id, motion.pair.b, now)
        if motion.pair.session_id != self.session_id or not provenance:
            raise ValueError("Motion session/provenance required")
        entry = self._entities.get(motion.track_id)
        if (
            entry is None
            or entry.identity != motion.pair.b
            or entry.track.observation_status != "OBSERVED"
        ):
            self._diagnostics.append("MOTION_TRACK_FRAME_MISMATCH")
            return
        if not all(
            isfinite(v)
            for v in (
                *motion.median_displacement_pixels,
                *motion.median_rate_pixels_per_second,
                *motion.mad_pixels,
            )
        ):
            raise ValueError("Nonfinite image motion")
        if (
            entry.motion is None
            or entry.motion.pair.b.observation_ns < motion.pair.b.observation_ns
        ):
            entry.motion, entry.motion_provenance = motion, provenance
            self._time = now

    def ingest_semantic(self, semantic: SemanticFrame, now: int) -> None:
        if self._accept("semantics", semantic.session_id, semantic.identity, now):
            labels, counts = np.unique(semantic.labels, return_counts=True)
            self._semantic_counts = tuple(
                (str(int(a)), int(b)) for a, b in zip(labels, counts, strict=True)
            )
            status = S.PROPAGATED if semantic.status.value == "PROPAGATED" else S.FRESH
            if semantic.status.value in {"STALE", "UNAVAILABLE"}:
                status = S(semantic.status.value)
            self._source(
                "semantics",
                semantic.observed_identity,
                (semantic.provenance,),
                semantic.status.value,
                semantic.quality.value,
                "UNVERIFIED",
                status,
            )
            for entry in self._entities.values():
                if (
                    entry.identity != semantic.identity
                    or entry.track.observation_status != "OBSERVED"
                ):
                    continue
                box = entry.track.latest_observed_bbox
                x, y = semantic.mapping.forward((box.x1 + box.x2) / 2, (box.y1 + box.y2) / 2)
                if not (0 <= x < semantic.labels.shape[1] and 0 <= y < semantic.labels.shape[0]):
                    continue
                label = C(int(semantic.labels[int(y), int(x)])).name
                entry.semantic_evidence = self._sources["semantics"]
                entry.semantic_label = label
                expected = {
                    "PERSON": "PERSON",
                    "BICYCLE": "BICYCLE",
                    "MOTORCYCLE": "MOTORCYCLE",
                    "CAR": "VEHICLE",
                    "BUS": "VEHICLE",
                    "TRUCK": "VEHICLE",
                    "TRAIN": "VEHICLE",
                }.get(entry.track.category.value)
                if expected and label not in {expected, "UNKNOWN", "BACKGROUND_OTHER"}:
                    self._diagnostics.append("SEMANTIC_CENTER_CATEGORY_DISAGREEMENT_UNVERIFIED")

    def ingest_surface(self, surface: SurfaceEvidenceFrame, now: int) -> None:
        if self.geometry and surface.camera_image_id != self.geometry.c.image_frame_id:
            raise ValueError("Surface camera mismatch")
        if self._accept("surface", surface.session_id, surface.identity, now):
            status = S.PROPAGATED if surface.status.value == "PROPAGATED" else S.FRESH
            if surface.status.value in {"STALE", "UNAVAILABLE"}:
                status = S(surface.status.value)
            provenance = tuple(
                p
                for p in (
                    surface.semantic_provenance,
                    surface.detection_provenance,
                    surface.track_provenance,
                )
                if p is not None
            )
            evidence = self._source(
                "surface",
                surface.observed_identity,
                provenance,
                surface.status.value,
                surface.quality.value,
                "UNVERIFIED",
                status,
            )
            self._surface = WorldSurfaceState(
                evidence,
                "UNVERIFIED",
                surface.camera_image_id,
                (surface.evidence.shape[1], surface.evidence.shape[0]),
                surface.regions[: self.config.max_regions],
                tuple(
                    (str(f.name), int(np.count_nonzero(surface.evidence & int(f))))
                    for f in SurfaceFlag
                ),
                (),
                samples=surface_samples(surface),
            )
            if len(surface.regions) > self.config.max_regions:
                self._diagnostics.append("SURFACE_REGION_CAP_REACHED")
            self._diagnostics.append("SEMANTIC_UNVERIFIED")

    def project_surface_pixel(
        self,
        session: str,
        identity: FrameIdentity,
        region_id: int,
        pixel: tuple[float, float],
        plane_point: tuple[float, float, float],
        plane_normal: tuple[float, float, float],
        plane_provenance: ComponentProvenance,
        now: int,
    ) -> None:
        """Optional supplied same-frame assumption. No plane fitting or path decision."""
        self._validate(session, identity, now)
        if (
            not all(isfinite(v) for v in (*pixel, *plane_point, *plane_normal))
            or sum(v * v for v in plane_normal) <= 0
        ):
            raise ValueError("Finite pixel/plane and nonzero normal required")
        surface, pose = self._surface, self._pose
        if (
            surface is None
            or pose is None
            or self.geometry is None
            or surface.evidence.identity != identity
            or pose.identity != identity
            or self._get("pose", now).status != S.FRESH
            or self._payload_source("surface", surface.evidence, now).status != S.FRESH
        ):
            self._diagnostics.append("GROUND_PROJECTION_INPUT_UNAVAILABLE")
            return
        region = next((r for r in surface.regions if r.region_id == region_id), None)
        if (
            region is None
            or not region.box.x1 <= pixel[0] < region.box.x2
            or not region.box.y1 <= pixel[1] < region.box.y2
        ):
            raise ValueError("Projection pixel outside referenced region box")
        point = self.geometry.ground_candidate(
            pixel,
            identity,
            pose.translation_meters,
            pose.rotation_wxyz,
            pose.world_frame_id,
            plane_point,
            plane_normal,
        )
        if point is None:
            self._diagnostics.append("GROUND_PROJECTION_UNAVAILABLE")
            return
        existing = tuple(p for p in surface.projected_ground if p.region_id != region_id)
        candidate = SurfaceGroundCandidate(
            region_id,
            pixel,
            point,
            identity,
            pose.world_frame_id,
            surface.evidence.provenance + self._get("pose", now).provenance + (plane_provenance,),
        )
        self._surface = replace(
            surface,
            projected_ground=existing + (candidate,),
            geometry_status="GROUND_PLANE_PROJECTED; SUPPLIED_ASSUMPTION; UNVERIFIED",
        )
        self._time = now

    def failure(self, source: str, session: str, identity: FrameIdentity, now: int) -> None:
        if source not in SOURCES:
            raise ValueError("Unknown subsystem")
        if self._accept(source, session, identity, now):
            self._source(source, identity, (), status=S.FAILED, reason="SOURCE_FAILURE")
            self._diagnostics.append(source.upper() + "_FAILED")

    def _prune(self, now: int) -> None:
        # Retention follows payload observation time, never the latest failure tick.
        if (
            self._surface
            and self._surface.evidence.identity
            and now - self._surface.evidence.identity.observation_ns > self.config.retention_ns
        ):
            self._surface = None
        if self._pose and now - self._pose.identity.observation_ns > self.config.retention_ns:
            self._pose = None
            self._pose_source = None
        if self._motion and now - self._motion.pair.b.observation_ns > self.config.retention_ns:
            self._motion = None
            self._motion_source = None
        for key, entry in tuple(self._entities.items()):
            if now - entry.track.latest_observed_ns > self.config.expire_ns:
                del self._entities[key]
                self.expired += 1
                continue
            while (
                entry.history
                and now - entry.history[0].identity.observation_ns > self.config.history_ns
            ):
                entry.history.popleft()
            if entry.depth and now - entry.depth.identity.observation_ns > self.config.retention_ns:
                entry.depth = entry.point = None
            if entry.motion and now - entry.motion.pair.b.observation_ns > self.config.retention_ns:
                entry.motion = None
                entry.motion_provenance = ()
            if (
                entry.semantic_evidence
                and entry.semantic_evidence.identity
                and now - entry.semantic_evidence.identity.observation_ns > self.config.retention_ns
            ):
                entry.semantic_evidence = None
                entry.semantic_label = None
        for source, value in tuple(self._sources.items()):
            if value.identity and now - value.identity.observation_ns > self.config.retention_ns:
                del self._sources[source]
                if source == "surface":
                    self._surface = None
                elif source == "semantics":
                    self._semantic_counts = ()
                elif source == "pose":
                    self._pose = None
                elif source == "motion":
                    self._motion = None

    def _entity(self, entry: _Entity, now: int) -> WorldEntity:
        t = entry.track
        age = now - t.latest_observed_ns
        observed = t.observation_status == "OBSERVED" and entry.identity.observation_ns == now
        lifecycle = EntityLifecycle.ACTIVE if observed else EntityLifecycle.PREDICTED
        if t.lifecycle == Lifecycle.TENTATIVE and observed:
            lifecycle = EntityLifecycle.TENTATIVE
        if age > self.config.lost_ns or t.lifecycle == Lifecycle.LOST:
            lifecycle = EntityLifecycle.LOST
        te = self._age(
            EvidenceSource(
                "tracking",
                entry.identity,
                0,
                S.FRESH if observed else S.PREDICTED,
                "OBSERVED" if observed else "PREDICTED",
                "UNCALIBRATED_TRACK_QUALITY",
                "UNVALIDATED",
                (entry.provenance, t.detector_provenance),
            ),
            now,
        )
        de = EvidenceSource(
            "depth", None, None, S.UNAVAILABLE, "UNAVAILABLE", "UNKNOWN", "UNVALIDATED"
        )
        estimate = entry.depth.estimate if entry.depth else None
        if estimate is not None:
            de = self._age(
                EvidenceSource(
                    "depth",
                    estimate.identity,
                    0,
                    S.FRESH,
                    "EXACT_FRAME",
                    estimate.quality,
                    "METRIC_DEPTH_UNVALIDATED"
                    if estimate.representation.kind == DepthKind.METRIC
                    else "RELATIVE_ONLY",
                    (estimate.provenance,),
                ),
                now,
                not observed or estimate.identity != entry.identity,
            )
            if self._get("depth", now).status == S.FAILED:
                de = replace(de, status=S.STALE, reason="SOURCE_FAILURE")
        point = entry.point
        wp = None
        pe = self._get("pose", now)
        position_sources: tuple[EvidenceSource, ...] = (de,)
        reasons = []
        if point is not None and self.geometry and self._pose and pe.status == S.FRESH:
            if point.identity == self._pose.identity and de.status == S.FRESH:
                wp = world_point(point, self.geometry, self._pose)
                position_sources = (de, pe)
            else:
                reasons.append("POSE_DEPTH_TIME_MISMATCH")
        if point is not None and wp is None:
            reasons.append("WORLD_POSITION_UNAVAILABLE")
        me = EvidenceSource(
            "motion", None, None, S.UNAVAILABLE, "UNAVAILABLE", "UNKNOWN", "UNVALIDATED"
        )
        if entry.motion:
            me = self._age(
                EvidenceSource(
                    "motion",
                    entry.motion.pair.b,
                    0,
                    S.DEGRADED,
                    "OBSERVED_IMAGE_RESIDUAL",
                    entry.motion.quality,
                    "PHYSICAL_MOTION_UNVALIDATED",
                    entry.motion_provenance,
                ),
                now,
                entry.motion.pair.b != entry.identity or not observed,
            )
        if not observed:
            reasons.append("TRACK_PREDICTED_ONLY")
        if de.status == S.STALE:
            reasons.append("DEPTH_STALE")
        return WorldEntity(
            entry.entity_id,
            t.track_id,
            t.category,
            t.category_confidence,
            lifecycle,
            "OBSERVED" if observed else "PREDICTED",
            t.latest_observed_ns,
            now,
            age,
            t.bbox,
            t.bearing_radians,
            te,
            estimate,
            de,
            point,
            wp,
            "UNAVAILABLE"
            if point is None
            else "OBSERVED_MODEL_ESTIMATE"
            if de.status == S.FRESH
            else "STALE_MODEL_ESTIMATE",
            position_sources,
            entry.motion,
            me,
            tuple(entry.history),
            "DEGRADED",
            tuple(reasons),
            self._payload_source("semantics", entry.semantic_evidence, now)
            if entry.semantic_evidence
            else None,
            entry.semantic_label,
            t.entity_observation,
            entry.concept_fusion.snapshot(now) if entry.concept_fusion else None,
        )

    def snapshot(self, timestamp: int) -> WorldState:
        self._owner_check()
        if self._closed or not 0 <= timestamp <= 2**63 - 1 or timestamp < self._time:
            raise ValueError("Snapshot time reversal requires explicit reset")
        if any(i.observation_ns > timestamp for i in self._watermarks.values()):
            raise ValueError("Snapshot precedes ingested evidence")
        self._time = timestamp
        self._prune(timestamp)
        entities = tuple(self._entity(e, timestamp) for _, e in sorted(self._entities.items()))
        sources = tuple(self._get(name, timestamp) for name in SOURCES)
        pose = self._payload_source("pose", self._pose_source if self._pose else None, timestamp)
        motion = self._payload_source(
            "motion", self._motion_source if self._motion else None, timestamp
        )
        m = self._motion
        camera = WorldCameraState(
            self._pose,
            pose,
            self._calibration_id,
            self.geometry.c.calibration_quality.state if self.geometry else "UNKNOWN",
            motion,
            (m.pair.a, m.pair.b) if m else None,
            tuple(float(x) for x in m.rotation.ravel())
            if m is not None and m.rotation is not None
            else None,
            tuple(float(x) for x in m.translation_direction)
            if m is not None and m.translation_direction is not None
            else None,
            m.scale_status if m else ScaleStatus.NONE,
        )
        surface = (
            replace(
                self._surface,
                evidence=self._payload_source("surface", self._surface.evidence, timestamp),
            )
            if self._surface
            else WorldSurfaceState(
                self._get("surface", timestamp), "UNVERIFIED", None, None, (), (), ()
            )
        )
        # Join class counts only when their source identities match.
        if surface.evidence.identity == self._get("semantics", timestamp).identity:
            surface = replace(surface, semantic_class_pixels=self._semantic_counts)
        capabilities = (
            Capability("HAS_TRACKING", self._get("tracking", timestamp).status, ()),
            Capability(
                "HAS_METRIC_DEPTH_ESTIMATE",
                S.DEGRADED
                if any(
                    e.depth is not None
                    and e.depth.representation.kind == DepthKind.METRIC
                    and e.depth_evidence.status == S.FRESH
                    for e in entities
                )
                else S.UNAVAILABLE,
                ("METRIC_DEPTH_UNVALIDATED",),
            ),
            Capability("HAS_CAMERA_POSE", pose.status, ("LOCAL_WORLD_DRIFT_UNVALIDATED",)),
            Capability("HAS_SEMANTIC_SURFACE", surface.evidence.status, ("SEMANTIC_UNVERIFIED",)),
            Capability("HAS_MOTION_EVIDENCE", motion.status, ("PHYSICAL_MOTION_UNVALIDATED",)),
        )
        reasons = tuple(
            s.subsystem.upper() + "_" + s.status.value for s in sources if s.status != S.FRESH
        )
        reasons += ("SEMANTIC_UNVERIFIED",) if self._surface else ()
        self.snapshots += 1
        return WorldState(
            self.session_id,
            timestamp,
            camera,
            entities,
            surface,
            WorldSceneQuality("DEGRADED" if entities or self._surface else "UNRELIABLE", reasons),
            tuple((s.subsystem, s.age_ns) for s in sources),
            sources,
            capabilities,
            self.provenance,
            tuple(self._diagnostics),
            image_geometry=WorldImageGeometry(
                self.geometry.c.image_frame_id,
                self.geometry.c.resolution.width,
                self.geometry.c.resolution.height,
                self._get("camera", timestamp),
            )
            if self.geometry
            else None,
        )

    def consume(self, result: FrameResult) -> WorldState:
        now = result.identity.observation_ns
        if self._accept("camera", self.session_id, result.identity, now):
            self._source("camera", result.identity, (), quality="SOURCE_TIMING_ONLY")
        if result.detector:
            self.ingest_detection(self.session_id, result.detector, now)
        if result.tracks:
            self.ingest_tracks(result.tracks, now)
        if result.depth and self._accept("depth", self.session_id, result.depth.identity, now):
            self._source(
                "depth",
                result.depth.identity,
                (result.depth.provenance,),
                validation="METRIC_DEPTH_UNVALIDATED"
                if result.depth.representation.kind == DepthKind.METRIC
                else "RELATIVE_ONLY",
            )
        for d in result.track_depths:
            self.ingest_depth(d, now)
        if result.camera_motion:
            self.ingest_camera_motion(result.camera_motion, now)
        for m in result.track_image_motion:
            provenance = tuple(
                p
                for p in (
                    result.optical_flow.provenance if result.optical_flow else None,
                    result.camera_motion.provenance if result.camera_motion else None,
                )
                if p is not None
            )
            self.ingest_image_motion(m, provenance, now)
        if result.segmentation:
            self.ingest_semantic(result.segmentation, now)
        if result.surfaces:
            self.ingest_surface(result.surfaces, now)
        for execution in result.components:
            if execution.status in {"FAILED", "RECOVERABLE_FAILURE"}:
                source = {"optical_flow": "motion", "segmentation": "semantics"}.get(
                    execution.provenance.component_type, execution.provenance.component_type
                )
                if source in SOURCES:
                    self.failure(source, self.session_id, result.identity, now)
        for error in result.errors:
            source = {"optical_flow": "motion", "segmentation": "semantics"}.get(
                error.split(":")[0], error.split(":")[0]
            )
            if source in SOURCES:
                self.failure(source, self.session_id, result.identity, now)
                if source == "semantics":
                    self.failure("surface", self.session_id, result.identity, now)
        return replace(self.snapshot(now), user_motion_heading=result.user_motion_heading)
