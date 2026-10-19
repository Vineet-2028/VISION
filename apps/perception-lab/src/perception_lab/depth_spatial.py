"""Depth-to-point boundary. No world motion, risk, uncertainty fabrication or fusion."""

from dataclasses import dataclass

from .contracts import FrameIdentity
from .depth import DepthAxis, DepthKind
from .depth_sampling import DepthEstimate
from .geometry import CoreGeometry


@dataclass(frozen=True)
class CameraPointEstimate:
    identity: FrameIdentity
    camera_frame_id: str
    position_meters: tuple[float, float, float]
    depth: DepthEstimate
    calibration_quality: str
    uncertainty_status: str = "UNKNOWN"


@dataclass(frozen=True)
class SuppliedDepthPose:
    """Exact observation pose supplied by a future synchronized pose adapter."""

    identity: FrameIdentity
    device_frame_id: str
    world_frame_id: str
    translation_meters: tuple[float, float, float]
    rotation_wxyz: tuple[float, float, float, float]


@dataclass(frozen=True)
class WorldPointEstimate:
    identity: FrameIdentity
    world_frame_id: str
    position_meters: tuple[float, float, float]
    camera_point: CameraPointEstimate
    uncertainty_status: str = "UNKNOWN"


def world_point(
    point: CameraPointEstimate, geometry: CoreGeometry, pose: SuppliedDepthPose | None
) -> WorldPointEstimate | None:
    if point.camera_frame_id != geometry.c.camera_frame_id:
        raise ValueError("Camera frame mismatch")
    if pose is None or geometry.c.camera_to_device is None:
        return None
    if pose.device_frame_id != geometry.c.camera_to_device.device_frame_id:
        raise ValueError("Pose device frame mismatch")
    transformed = geometry.depth_world_point(
        point.position_meters,
        point.identity,
        pose.identity,
        pose.translation_meters,
        pose.rotation_wxyz,
        pose.world_frame_id,
    )
    if transformed is None:
        return None
    return WorldPointEstimate(point.identity, pose.world_frame_id, transformed, point)


def camera_point(estimate: DepthEstimate, geometry: CoreGeometry) -> CameraPointEstimate | None:
    if estimate.camera_image_id != geometry.c.image_frame_id or estimate.camera_dimensions != (
        geometry.c.resolution.width,
        geometry.c.resolution.height,
    ):
        raise ValueError("Depth estimate/calibration image mismatch")
    if estimate.representation.kind != DepthKind.METRIC:
        return None
    point = geometry.depth_point(
        *estimate.sample_pixel,
        estimate.meters,
        estimate.representation.axis == DepthAxis.CAMERA_Z,
        estimate.identity,
    )
    if point is None:
        return None
    return CameraPointEstimate(
        estimate.identity,
        geometry.c.camera_frame_id,
        point,
        estimate,
        geometry.c.calibration_quality.state,
    )
