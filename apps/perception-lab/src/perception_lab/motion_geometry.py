"""Typed motion use of Guardian calibrated rays/projections; no vendor geometry."""

import numpy as np
from numpy.typing import NDArray

from .config import canonical_hash
from .depth import DepthAxis, DepthFrame, DepthKind
from .depth_sampling import sample_pixel
from .flow import FramePair, SparseFlowObservation
from .geometry import CoreGeometry
from .motion import CameraMotionEstimate, ResidualFlow, ScaleStatus


def calibration_hash(geometry: CoreGeometry) -> str:
    return canonical_hash(geometry.c.model_dump(exclude={"metadata"}))


def require_calibration(geometry: CoreGeometry, pair: FramePair) -> None:
    if (
        pair.calibration_hash != calibration_hash(geometry)
        or pair.camera_image_id != geometry.c.image_frame_id
        or (pair.width, pair.height) != (geometry.c.resolution.width, geometry.c.resolution.height)
    ):
        raise ValueError("Motion calibration identity mismatch")


def rays(geometry: CoreGeometry, flow: SparseFlowObservation, which: str) -> NDArray[np.float64]:
    require_calibration(geometry, flow.pair)
    points, identity = (
        (flow.points_a, flow.pair.a) if which == "a" else (flow.points_b, flow.pair.b)
    )
    result = np.full((len(points), 3), np.nan)
    metadata = geometry.metadata(identity)
    for i, (u, v) in enumerate(points):
        ray = geometry.model.pixelToCameraRay(
            geometry.j["PixelPoint"](geometry.image, float(u), float(v)), metadata
        )
        if ray.isPresent():
            r = ray.get()
            result[i] = [r.x(), r.y(), r.z()]
    return result


def project(geometry: CoreGeometry, points: NDArray[np.float64]) -> NDArray[np.float64]:
    result = np.full((len(points), 2), np.nan)
    for i, xyz in enumerate(points):
        if not np.isfinite(xyz).all():
            continue
        p = geometry.model.cameraPointToPixel(
            geometry.j["Vector3"](geometry.camera, *map(float, xyz))
        )
        if p.isValid():
            result[i] = [p.pixel().get().u(), p.pixel().get().v()]
    return result


def depth_points(
    geometry: CoreGeometry, flow: SparseFlowObservation, depth: DepthFrame
) -> NDArray[np.float64]:
    require_calibration(geometry, flow.pair)
    if (
        depth.identity != flow.pair.a
        or depth.representation.kind != DepthKind.METRIC
        or depth.mapping.camera_image_id != flow.pair.camera_image_id
        or depth.mapping.camera_dimensions != (flow.pair.width, flow.pair.height)
    ):
        raise ValueError("PnP requires exact frame-A metric depth and matching camera")
    xyz = np.full((len(flow.valid), 3), np.nan)
    for i, (u, v) in enumerate(flow.points_a):
        value = sample_pixel(depth, float(u), float(v))
        if value is not None:
            point = geometry.depth_point(
                float(u),
                float(v),
                value,
                depth.representation.axis == DepthAxis.CAMERA_Z,
                flow.pair.a,
            )
            if point is not None:
                xyz[i] = point
    return xyz


def compensate(
    geometry: CoreGeometry,
    flow: SparseFlowObservation,
    motion: CameraMotionEstimate,
    depth: DepthFrame | None = None,
) -> ResidualFlow | None:
    require_calibration(geometry, flow.pair)
    if flow.pair != motion.pair:
        raise ValueError("Motion/flow pair mismatch")
    if geometry.c.calibration_quality.state not in {"VALID", "DEGRADED"}:
        return None
    if motion.rotation is None:
        return None
    points = rays(geometry, flow, "a")
    kind = "ROTATION_ONLY"
    if motion.scale_status == ScaleStatus.DEPTH_SCALED_RESEARCH:
        if depth is None:
            raise ValueError("Research translation requires matching frame-A depth")
        points = depth_points(geometry, flow, depth)
        kind = "DEPTH_SCALED_RESEARCH_UNVALIDATED_SCALE"
    predicted = points @ motion.rotation.T
    if kind != "ROTATION_ONLY":
        assert motion.research_translation is not None
        predicted += motion.research_translation
    pixels = project(geometry, predicted)
    valid = flow.valid & np.isfinite(pixels).all(axis=1)
    expected = np.nan_to_num(pixels - flow.points_a, nan=0)
    return ResidualFlow(
        flow.pair,
        flow.points_b,
        flow.displacement - expected,
        expected,
        valid,
        kind,
        flow.provenance,
        motion.provenance,
    )
