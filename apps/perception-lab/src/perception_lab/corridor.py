"""Stateless, bounded WorldState -> geometric relevance. No vendor/runtime imports."""

from functools import lru_cache
from math import hypot, isfinite

import numpy as np

from . import __version__
from .config import canonical_hash
from .contracts import ComponentProvenance
from .corridor_config import CorridorConfig
from .corridor_types import (
    CorridorAnalysis,
    CorridorMode,
    CorridorSurfaceEvidence,
    EntityCorridorRelation,
    FreeSpaceEvidence,
    InteractionZone,
    Point2,
    Relation,
    UserCorridorState,
)
from .depth import DepthKind
from .geometry import CoreCorridor, CoreGeometry
from .world_types import EvidenceSource, EvidenceStatus, WorldEntity, WorldState


def clip_rect(
    polygon: tuple[Point2, ...], bounds: tuple[float, float, float, float]
) -> tuple[Point2, ...]:
    """Clip compact continuous-edge image polygons, never metric transforms."""
    result = list(polygon)
    for axis, limit, sign in (
        (0, bounds[0], 1),
        (0, bounds[2], -1),
        (1, bounds[1], 1),
        (1, bounds[3], -1),
    ):
        previous = result
        result = []
        if not previous:
            break
        a = previous[-1]
        for b in previous:
            ai, bi = sign * (a[axis] - limit) >= 0, sign * (b[axis] - limit) >= 0
            if ai != bi:
                t = (limit - a[axis]) / (b[axis] - a[axis])
                result.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
            if bi:
                result.append(b)
            a = b
    return tuple(result)


def _prepare_polygon_edges(polygon: tuple[Point2, ...]) -> tuple[tuple[float, ...], ...]:
    edges = []
    for i, a in enumerate(polygon):
        b = polygon[(i + 1) % len(polygon)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        edges.append((a[0], a[1], dx, dy, dx * dx + dy * dy))
    return tuple(edges)


_polygon_edges = lru_cache(maxsize=32)(_prepare_polygon_edges)


def image_distance(point: Point2, polygon: tuple[Point2, ...]) -> float:
    """Signed Euclidean pixel distance: negative inside, zero on boundary."""
    positive = negative = True
    distance: float | None = None
    # Bound retained vertices as well as entry count. Larger polygons preserve
    # the original calculation but are never retained by the shared cache.
    edges = _polygon_edges(polygon) if len(polygon) <= 16 else _prepare_polygon_edges(polygon)
    for ax, ay, dx, dy, length in edges:
        px, py = point[0] - ax, point[1] - ay
        sign = dx * py - dy * px
        positive = positive and sign >= -1e-9
        negative = negative and sign <= 1e-9
        t = (px * dx + py * dy) / length if length else 0.0
        # Preserve min(1.0, t), then max(0.0, t), including NaN/zero ordering.
        t = t if t < 1.0 else 1.0
        t = t if t > 0.0 else 0.0
        current = hypot(px - t * dx, py - t * dy)
        if distance is None or current < distance:
            distance = current
    if distance is None:
        raise ValueError("Empty polygon")
    return distance * (-1 if positive or negative else 1)


def usable(source: EvidenceSource, now: int, limit: int) -> bool:
    return (
        source.identity is not None
        and source.age_ns is not None
        and 0 <= now - source.identity.observation_ns <= limit
        and source.age_ns == now - source.identity.observation_ns
        and source.status in {EvidenceStatus.FRESH, EvidenceStatus.DEGRADED}
        and source.quality not in {"UNAVAILABLE", "UNRELIABLE", "FAILED"}
    )


class HybridCorridorAnalyzer:
    def __init__(self, config: CorridorConfig, geometry: CoreGeometry | None = None) -> None:
        self.config, self.geometry = config, geometry
        self.calibration_id = (
            canonical_hash(geometry.c.model_dump(exclude={"metadata"})) if geometry else None
        )
        self.provenance = ComponentProvenance(
            "HybridCorridorAnalyzer",
            "corridor",
            "deterministic-v1",
            __version__,
            "python+guardian",
            canonical_hash(config.model_dump()),
        )

    def _metric(self, s: WorldState) -> tuple[CoreCorridor | None, tuple[str, ...]]:
        c, g, plane, camera = self.config, self.geometry, s.ground_plane, s.camera_state
        if c.mode == "IMAGE":
            return None, ("CONFIGURED_IMAGE_MODE",)
        if (
            g is None
            or camera.calibration_quality not in {"VALID", "DEGRADED"}
            or camera.calibration_id != self.calibration_id
        ):
            return None, ("CALIBRATION_UNAVAILABLE",)
        if plane is None:
            return None, ("GROUND_PLANE_UNAVAILABLE",)
        image = s.image_geometry
        if (
            image is None
            or image.camera_image_id != g.c.image_frame_id
            or (image.width, image.height) != (g.c.resolution.width, g.c.resolution.height)
        ):
            return None, ("IMAGE_FRAME_MISMATCH",)
        reference = image.evidence.identity
        identity = plane.evidence.identity
        if (
            identity is None
            or reference is None
            or identity != reference
            or identity.observation_ns != s.state_timestamp
            or not usable(image.evidence, s.state_timestamp, c.fresh_ns)
            or not usable(plane.evidence, s.state_timestamp, c.fresh_ns)
        ):
            return None, ("GROUND_PLANE_TIME_MISMATCH",)
        if not all(isfinite(v) for v in (*plane.point_meters, *plane.normal)):
            return None, ("GROUND_PLANE_INVALID",)
        pose = camera.pose
        if plane.coordinate_frame == "LOCAL_WORLD":
            if (
                pose is None
                or pose.identity != identity
                or pose.world_frame_id != plane.frame_id
                or not usable(camera.pose_evidence, s.state_timestamp, c.fresh_ns)
                or camera.pose_evidence.identity != identity
                or g.c.camera_to_device is None
                or pose.device_frame_id != g.c.camera_to_device.device_frame_id
                or not all(isfinite(v) for v in (*pose.rotation_wxyz, *pose.translation_meters))
                or abs(sum(v * v for v in pose.rotation_wxyz) - 1) > 1e-8
            ):
                return None, ("POSE_STALE_OR_INVALID",)
        elif plane.coordinate_frame != "CAMERA" or plane.frame_id != g.c.camera_frame_id:
            return None, ("GROUND_FRAME_MISMATCH",)
        heading = s.user_motion_heading
        direction = None
        heading_reason = "USER_HEADING_UNAVAILABLE"
        if heading is not None:
            if (
                heading.identity == reference
                and heading.coordinate_frame == g.c.camera_frame_id
                and heading.quality in {"GOOD", "DEGRADED"}
                and heading.source == "VISUAL_CAMERA_TRANSLATION_PROJECTED_ON_SUPPLIED_GROUND"
                and heading.age_ns == 0
                and heading.direction is not None
                and len(heading.direction) == 3
                and all(isfinite(v) for v in heading.direction)
                and abs(sum(v * v for v in heading.direction) - 1) <= 1e-6
            ):
                direction = heading.direction
                heading_reason = "USER_TRAVEL_DIRECTION; RIGID_MOUNT_ASSUMPTION_UNVALIDATED"
            else:
                heading_reason = "USER_HEADING_UNUSABLE"
        try:
            return g.corridor(plane, pose, c, camera_heading=direction), (
                "GROUND_PLANE_ASSUMPTION",
                heading_reason,
                "PHYSICAL_GEOMETRY_UNVALIDATED",
            ) + (() if direction is not None else ("CAMERA_FORWARD_NOT_BODY_HEADING",))
        except ValueError:
            return None, ("GROUND_HEADING_DEGENERATE",)

    def analyze(self, state: WorldState) -> CorridorAnalysis:
        if state.schema_version != 1:
            raise ValueError("Unsupported WorldState schema")
        if (
            not state.session_id
            or not 0 <= state.state_timestamp <= 2**63 - 1
            or len(state.entities) > 512
        ):
            raise ValueError("Invalid bounded WorldState")
        if len({e.entity_id for e in state.entities}) != len(state.entities) or any(
            e.entity_id.session_id != state.session_id for e in state.entities
        ):
            raise ValueError("Entity session/identity mismatch")
        image, now, c = state.image_geometry, state.state_timestamp, self.config
        if image and (not 0 < image.width <= 32768 or not 0 < image.height <= 32768):
            raise ValueError("Invalid image dimensions")
        if len(state.surface_state.samples) > 768:
            raise ValueError("Surface sample capacity exceeded")
        core, reasons = self._metric(state)
        heading = (
            state.camera_state.pose_evidence
            if core and state.ground_plane and state.ground_plane.coordinate_frame == "LOCAL_WORLD"
            else (image.evidence if image else state.camera_state.pose_evidence)
        )
        if core and "USER_TRAVEL_DIRECTION; RIGID_MOUNT_ASSUMPTION_UNVALIDATED" in reasons:
            estimate = state.user_motion_heading
            assert estimate is not None
            heading = EvidenceSource(
                "user_heading",
                estimate.identity,
                estimate.age_ns,
                EvidenceStatus.DEGRADED,
                "OBSERVED",
                "DEGRADED",
                "UNVERIFIED",
                (estimate.provenance,),
            )
        polygon: tuple[Point2, ...] = ()
        mode = CorridorMode.IMAGE
        frame = image.camera_image_id if image else "IMAGE_UNAVAILABLE"
        vertices: tuple[tuple[float, float, float], ...] = ()
        if core and state.ground_plane:
            mode = (
                CorridorMode.WORLD
                if state.ground_plane.coordinate_frame == "LOCAL_WORLD"
                else CorridorMode.GROUND
            )
            frame = state.ground_plane.frame_id
            vertices = core.polygon
            polygon = core.project()
            if image and polygon:
                polygon = clip_rect(polygon, (0, 0, image.width, image.height))
            if not polygon:
                reasons += ("IMAGE_PROJECTION_UNAVAILABLE",)
        elif image:
            w, h = image.width, image.height
            polygon = (
                (w * (0.5 - c.image_bottom_half_width), float(h)),
                (w * (0.5 + c.image_bottom_half_width), float(h)),
                (w * (0.5 + c.image_top_half_width), h * c.image_top),
                (w * (0.5 - c.image_top_half_width), h * c.image_top),
            )
            vertices = tuple((x, y, 0.0) for x, y in polygon)
            reasons += ("IMAGE_SPACE_ONLY", "CAMERA_FORWARD_NOT_BODY_HEADING")
        else:
            reasons += ("IMAGE_GEOMETRY_UNAVAILABLE",)
        quality = "DEGRADED" if vertices else "UNAVAILABLE"
        if image and not usable(image.evidence, now, c.fresh_ns):
            quality = "UNRELIABLE" if vertices else "UNAVAILABLE"
            reasons += ("CAMERA_EVIDENCE_UNAVAILABLE_OR_STALE",)
        corridor = UserCorridorState(
            now,
            mode,
            InteractionZone(state.session_id + ":forward", "USER_CORRIDOR", frame, vertices),
            polygon,
            core.origin if core else None,
            core.forward if core else None,
            core.lateral if core else None,
            c.near_m if core else None,
            c.far_m if core else None,
            c.near_half_width_m + c.expansion_m if core else None,
            c.far_half_width_m + c.expansion_m if core else None,
            "USER_TRAVEL_DIRECTION"
            if core and "USER_TRAVEL_DIRECTION; RIGID_MOUNT_ASSUMPTION_UNVALIDATED" in reasons
            else "POSE_CAMERA_FORWARD"
            if mode == CorridorMode.WORLD
            else "CAMERA_FORWARD",
            heading,
            state.ground_plane.evidence if core and state.ground_plane else None,
            quality,
            reasons,
        )
        relations = tuple(self._relation(e, state, corridor, core) for e in state.entities)
        surface = self._surface(state, corridor)
        occupied = tuple(
            r.entity_id for r in relations if r.relation in {Relation.INSIDE, Relation.INTERSECTS}
        )
        states = ["UNKNOWN"]  # Unseen/occluded volume is always unknown.
        if surface.candidate_ground_fraction:
            states.append("AVAILABLE_EVIDENCE")
        if occupied or surface.obstacle_evidence_fraction:
            states.append("OCCUPIED_EVIDENCE")
        return CorridorAnalysis(
            state.session_id,
            now,
            corridor,
            relations,
            surface,
            FreeSpaceEvidence(now, tuple(states), occupied, surface.unknown_fraction),
            quality,
            self.provenance,
            state.provenance,
            state.camera_state.calibration_id,
            state.schema_version,
        )

    def _relation(
        self, e: WorldEntity, s: WorldState, corridor: UserCorridorState, core: CoreCorridor | None
    ) -> EntityCorridorRelation:
        now, c = s.state_timestamp, self.config
        relation, source, basis = Relation.UNKNOWN, "UNAVAILABLE", "UNAVAILABLE"
        forward = lateral = boundary = None
        assumptions: tuple[str, ...] = ()
        sources: tuple[EvidenceSource, ...] = (e.track_evidence,)
        fresh = (
            e.state_timestamp == now
            and 0 <= e.observation_age_ns <= c.fresh_ns
            and e.observation_age_ns == now - e.latest_observed_ns
            and e.lifecycle.value != "LOST"
            and e.track_evidence.status
            not in {
                EvidenceStatus.FAILED,
                EvidenceStatus.UNAVAILABLE,
                EvidenceStatus.UNRELIABLE,
                EvidenceStatus.STALE,
            }
            and s.image_geometry is not None
            and e.track_evidence.identity is not None
            and 0 <= now - e.track_evidence.identity.observation_ns <= c.fresh_ns
            and s.image_geometry.evidence.identity is not None
            and e.track_evidence.identity.source_id == s.image_geometry.evidence.identity.source_id
            and e.track_evidence.identity.timing == s.image_geometry.evidence.identity.timing
        )
        point = e.position_world if corridor.mode == CorridorMode.WORLD else e.position_camera
        if (
            fresh
            and core
            and (
                e.entity_observation is not None
                or e.category.value in {"PERSON", "BICYCLE", "MOTORCYCLE", "CAR", "BUS", "TRUCK"}
            )
            and point is not None
            and e.depth is not None
            and e.depth.representation.kind == DepthKind.METRIC
            and usable(e.depth_evidence, now, c.fresh_ns)
            and point.identity.observation_ns == now
            and point.identity == e.track_evidence.identity
            and point.identity == e.depth_evidence.identity
            and e.position_camera is not None
            and e.position_camera.calibration_quality in {"VALID", "DEGRADED"}
            and e.position_camera.position_meters[2] > 0
            and all(usable(source, now, c.fresh_ns) for source in e.position_sources)
            and getattr(point, "world_frame_id", getattr(point, "camera_frame_id", None))
            == corridor.zone.coordinate_frame
            and all(isfinite(v) for v in point.position_meters)
            and (
                e.entity_observation is None
                or abs(core.plane_distance(point.position_meters)) <= c.generic_ground_tolerance_m
            )
        ):
            lateral, forward, boundary = core.locate(point.position_meters)
            relation = (
                Relation.NEAR_BOUNDARY
                if abs(boundary) <= c.boundary_m
                else Relation.INSIDE
                if boundary < 0
                else Relation.OUTSIDE
            )
            source, basis = "OBJECT_DEPTH_POINT; NOT_GROUND_CONTACT", corridor.zone.coordinate_frame
            assumptions = (
                "POINT_NEAR_SUPPLIED_GROUND_PLANE"
                if e.entity_observation is not None
                else "GROUNDED_CLASS_ASSUMPTION",
                "POINT_NOT_PHYSICAL_FOOTPRINT",
                "POINT_PROXIMITY_NOT_GROUND_CONTACT"
                if e.entity_observation is not None
                else "HEIGHT_NOT_TESTED",
                "METRIC_DEPTH_UNVALIDATED",
            )
            sources += (e.depth_evidence,) + e.position_sources
        elif fresh and corridor.image_polygon and s.image_geometry:
            box = e.image_geometry
            if (
                all(isfinite(v) for v in (box.x1, box.y1, box.x2, box.y2))
                and box.x2 > box.x1
                and box.y2 > box.y1
            ):
                pixel = ((box.x1 + box.x2) / 2, box.y2)
                if (
                    0 <= pixel[0] <= s.image_geometry.width
                    and 0 <= pixel[1] <= s.image_geometry.height
                ):
                    d = image_distance(pixel, corridor.image_polygon)
                    band = c.image_boundary_fraction * s.image_geometry.width
                    relation = (
                        Relation.NEAR_BOUNDARY
                        if abs(d) <= band
                        else Relation.INSIDE
                        if d < 0
                        else Relation.INTERSECTS
                        if len(clip_rect(corridor.image_polygon, (box.x1, box.y1, box.x2, box.y2)))
                        >= 3
                        else Relation.OUTSIDE
                    )
                    source, basis = "IMAGE_BBOX_BOTTOM_CENTER", "IMAGE_SPACE_RELATION"
                    assumptions = (
                        "IMAGE_LOCATION_NOT_GROUND_CONTACT",
                        "BBOX_OVERLAP_NOT_PHYSICAL_EXTENT",
                    )
        return EntityCorridorRelation(
            e.entity_id,
            now,
            relation,
            basis,
            source,
            forward,
            lateral,
            boundary,
            "UNRELIABLE"
            if e.observation_status != "OBSERVED" or relation == Relation.UNKNOWN
            else "DEGRADED",
            sources,
            assumptions,
        )

    def _surface(self, s: WorldState, corridor: UserCorridorState) -> CorridorSurfaceEvidence:
        surface, image = s.surface_state, s.image_geometry
        ground = traversable = obstacle = None
        unknown, count, quality = 1.0, 0, "UNAVAILABLE"
        if (
            image
            and len(corridor.image_polygon) >= 3
            and usable(image.evidence, s.state_timestamp, self.config.fresh_ns)
            and surface.samples
            and surface.camera_image_id == image.camera_image_id
            and surface.dimensions == (image.width, image.height)
            and usable(surface.evidence, s.state_timestamp, self.config.surface_fresh_ns)
            and surface.evidence.identity is not None
            and image.evidence.identity is not None
            and surface.evidence.identity.source_id == image.evidence.identity.source_id
            and surface.evidence.identity.timing == image.evidence.identity.timing
            and surface.evidence.identity == image.evidence.identity
        ):
            samples = np.asarray(surface.samples)
            if (
                not np.isfinite(samples).all()
                or np.any(samples[:, 2] < 0)
                or np.any(samples[:, 2] > 63)
                or np.any(samples[:, 2] != np.floor(samples[:, 2]))
            ):
                raise ValueError("Invalid surface samples")
            positive, negative = np.ones(len(samples), bool), np.ones(len(samples), bool)
            for i, a in enumerate(corridor.image_polygon):
                b = corridor.image_polygon[(i + 1) % len(corridor.image_polygon)]
                side = (b[0] - a[0]) * (samples[:, 1] - a[1]) - (b[1] - a[1]) * (
                    samples[:, 0] - a[0]
                )
                positive &= side >= 0
                negative &= side <= 0
            valid = (
                (positive | negative)
                & (samples[:, 0] >= 0)
                & (samples[:, 0] < image.width)
                & (samples[:, 1] >= 0)
                & (samples[:, 1] < image.height)
            )
            flags = samples[valid, 2].astype(np.uint8)
            count = len(flags)
            if count:
                ground = float(np.count_nonzero(flags & 2)) / count
                traversable = (
                    float(np.count_nonzero((flags & 4 != 0) & (flags & (1 | 8 | 16) == 0))) / count
                )
                obstacle = float(np.count_nonzero(flags & (8 | 16))) / count
                unknown = (
                    float(np.count_nonzero((flags & 1 != 0) | (flags & (2 | 4 | 8 | 16) == 0)))
                    / count
                )
                quality = "DEGRADED"
        return CorridorSurfaceEvidence(
            s.state_timestamp,
            corridor.zone.zone_id,
            ground,
            traversable,
            obstacle,
            unknown,
            count,
            surface.evidence,
            quality,
        )
