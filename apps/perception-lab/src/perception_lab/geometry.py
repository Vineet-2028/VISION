"""The only dynamic JNI boundary. All geometry executes in guardian-core.

Any is confined to foreign Java objects here; callers get typed Python wrappers.
The JVM is process-scoped, started once on the owning/main thread, never per frame.
"""

from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

import jpype
import numpy as np
from numpy.typing import NDArray

from .config import Calibration, Resolution, canonical_hash
from .contracts import FrameIdentity, LabError
from .detection import Box, Detection

if TYPE_CHECKING:
    from .corridor_config import CorridorConfig
    from .depth_spatial import SuppliedDepthPose
    from .interaction_types import RelativeMotionValues
    from .world_types import SuppliedGroundPlane


class CoreCorridor:
    """Typed wrapper around one immutable Guardian corridor and transform."""

    def __init__(self, corridor: Any, camera_to_frame: Any, geometry: "CoreGeometry") -> None:
        self._value, self._transform, self._geometry = corridor, camera_to_frame, geometry
        self._vector = geometry.j["Vector3"]
        self._frame = corridor.origin().frame()

    @staticmethod
    def _tuple(value: Any) -> tuple[float, float, float]:
        return float(value.x()), float(value.y()), float(value.z())

    @property
    def origin(self) -> tuple[float, float, float]:
        return self._tuple(self._value.origin())

    @property
    def forward(self) -> tuple[float, float, float]:
        return self._tuple(self._value.forward())

    @property
    def lateral(self) -> tuple[float, float, float]:
        return self._tuple(self._value.right())

    @property
    def polygon(self) -> tuple[tuple[float, float, float], ...]:
        return tuple(self._tuple(p) for p in self._value.polygon())

    def locate(self, point: tuple[float, float, float]) -> tuple[float, float, float]:
        result = self._value.locate(self._vector(self._frame, *point))
        return float(result[0]), float(result[1]), float(result[2])

    def plane_distance(self, point: tuple[float, float, float]) -> float:
        """Signed distance via Guardian; a point near a plane is not an object footprint."""
        plane = jpype.JClass("dev.sentinel.guardian.Plane3D")(
            self._value.origin(), self._value.right().cross(self._value.forward())
        )
        return float(plane.signedDistance(self._vector(self._frame, *point)))

    def project(self) -> tuple[tuple[float, float], ...]:
        # Reject a near-plane crossing conservatively; never project behind-camera vertices.
        inverse = self._transform.inverse() if self._transform is not None else None
        points = []
        for vertex in self._value.polygon():
            camera = inverse.transformPoint(vertex) if inverse is not None else vertex
            projection = self._geometry.model.cameraPointToPixel(camera)
            if not projection.isValid():
                return ()
            pixel = projection.pixel().get()
            points.append((float(pixel.u()), float(pixel.v())))
        return tuple(points)


class ImageMapping:
    def __init__(self, java_transform: Any, pixel_class: Any) -> None:
        self._transform = java_transform
        self._pixel = pixel_class
        # ImageTransform is affine. Cache Java-evaluated basis for bounded batched
        # sampling without hundreds of JNI calls per object.
        self._basis = (self.forward(0, 0), self.forward(1, 0), self.forward(0, 1))

    def forward_many(
        self, u: NDArray[np.float64], v: NDArray[np.float64]
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        origin, x, y = self._basis
        return (
            origin[0] + u * (x[0] - origin[0]) + v * (y[0] - origin[0]),
            origin[1] + u * (x[1] - origin[1]) + v * (y[1] - origin[1]),
        )

    @property
    def target_dimensions(self) -> tuple[int, int]:
        return int(self._transform.to().width()), int(self._transform.to().height())

    @property
    def camera_dimensions(self) -> tuple[int, int]:
        return int(self._transform.from_().width()), int(self._transform.from_().height())

    @property
    def camera_image_id(self) -> str:
        return str(self._transform.from_().frame().id())

    def scaled(self, width: int, height: int) -> "ImageMapping":
        frame = jpype.JClass("dev.sentinel.guardian.FrameId")
        kind = jpype.JClass("dev.sentinel.guardian.FrameKind").IMAGE
        size = jpype.JClass("dev.sentinel.guardian.ImageSize")
        transform = jpype.JClass("dev.sentinel.guardian.ImageTransform")
        target = size(frame(kind, "depth-native"), width, height)
        return ImageMapping(
            self._transform.then(transform.scale(self._transform.to(), target)), self._pixel
        )

    def resized_padded(self, width: int, height: int, resized: tuple[int, int]) -> "ImageMapping":
        """Exact integer resize followed by top-left padding (YOLOX/PicoDet boundary)."""
        frame = jpype.JClass("dev.sentinel.guardian.FrameId")
        kind = jpype.JClass("dev.sentinel.guardian.FrameKind").IMAGE
        size = jpype.JClass("dev.sentinel.guardian.ImageSize")
        transform = jpype.JClass("dev.sentinel.guardian.ImageTransform")
        intermediate = size(frame(kind, "edge-detector-resized"), *resized)
        target = size(frame(kind, "edge-detector-input"), width, height)
        combined = self._transform.then(transform.scale(self._transform.to(), intermediate)).then(
            transform.pad(intermediate, target, 0, 0)
        )
        return ImageMapping(combined, self._pixel)

    def letterboxed(
        self, width: int, height: int
    ) -> tuple["ImageMapping", tuple[int, int, int, int]]:
        source = self._transform.to()
        scale = min(width / int(source.width()), height / int(source.height()))
        resized_width = max(1, round(int(source.width()) * scale))
        resized_height = max(1, round(int(source.height()) * scale))
        left, top = (width - resized_width) // 2, (height - resized_height) // 2
        frame = jpype.JClass("dev.sentinel.guardian.FrameId")
        kind = jpype.JClass("dev.sentinel.guardian.FrameKind").IMAGE
        size = jpype.JClass("dev.sentinel.guardian.ImageSize")
        transform = jpype.JClass("dev.sentinel.guardian.ImageTransform")
        resized = size(frame(kind, "detector-resized"), resized_width, resized_height)
        tensor = size(frame(kind, "detector-tensor"), width, height)
        combined = self._transform.then(transform.scale(source, resized)).then(
            transform.pad(resized, tensor, left, top)
        )
        return ImageMapping(combined, self._pixel), (resized_width, resized_height, left, top)

    @property
    def fingerprint(self) -> str:
        # Three non-collinear points fully specify this affine transform. Include dimensions.
        return canonical_hash(
            {
                "from": [
                    int(self._transform.from_().width()),
                    int(self._transform.from_().height()),
                ],
                "to": [int(self._transform.to().width()), int(self._transform.to().height())],
                "basis": [self.forward(0, 0), self.forward(1, 0), self.forward(0, 1)],
                "convention": "continuous_edges",
                "from_frame": str(self._transform.from_().frame().id()),
                "to_frame": str(self._transform.to().frame().id()),
            }
        )

    def restore_box(self, box: Box) -> Box:
        # Every corner goes through Task003 ImageTransform, including rotated transforms.
        points = [
            self.inverse(u, v)
            for u, v in ((box.x1, box.y1), (box.x2, box.y1), (box.x1, box.y2), (box.x2, box.y2))
        ]
        return Box(
            min(p[0] for p in points),
            min(p[1] for p in points),
            max(p[0] for p in points),
            max(p[1] for p in points),
        )

    def forward(self, u: float, v: float) -> tuple[float, float]:
        point = self._transform.forward(self._pixel(self._transform.from_().frame(), u, v))
        return float(point.u()), float(point.v())

    def inverse(self, u: float, v: float) -> tuple[float, float]:
        point = self._transform.inverse().forward(self._pixel(self._transform.to().frame(), u, v))
        return float(point.u()), float(point.v())


class CoreGeometry:
    def cardinal_geometry(
        self, quarter_turns: int
    ) -> tuple[ImageMapping, tuple[float, float, float, float], tuple[float, ...]]:
        """Task003 rotation and optical basis; never silently reuse distorted intrinsics."""
        if type(quarter_turns) is not int or not 0 <= quarter_turns <= 3:
            raise ValueError("Quarter turns must be 0..3")
        if self.source_mapping is not None:
            raise ValueError("Scaled-source canonical intrinsics require explicit composition")
        j = self.j
        image = j["FrameId"](j["FrameKind"].IMAGE, f"v02-canonical-image-{quarter_turns}")
        camera = j["FrameId"](j["FrameKind"].CAMERA, f"v02-canonical-camera-{quarter_turns}")
        rotated = jpype.JClass("dev.sentinel.guardian.RotatedIntrinsics")(
            self.model.calibration().intrinsics(), image, camera, quarter_turns
        )
        k = rotated.intrinsics()
        transform = rotated.originalCameraToRotatedCamera()
        columns = [
            self._vector_tuple(transform.transformDirection(j["Vector3"](self.camera, *axis)))
            for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1))
        ]
        basis = tuple(columns[col][row] for row in range(3) for col in range(3))
        return (
            ImageMapping(rotated.imageTransform(), j["PixelPoint"]),
            (float(k.fxPixels()), float(k.fyPixels()), float(k.cxPixels()), float(k.cyPixels())),
            basis,
        )

    @staticmethod
    def _vector_tuple(value: Any) -> tuple[float, float, float]:
        return float(value.x()), float(value.y()), float(value.z())

    def relative_motion(
        self,
        frame_id: str,
        position: tuple[float, ...],
        velocity: tuple[float, ...],
        reference_position: tuple[float, ...],
        reference_velocity: tuple[float, ...],
    ) -> "RelativeMotionValues":
        """All relative motion/TTC/CPA equations stay in Guardian, including signed CPA."""
        from .interaction_types import RelativeMotionValues

        motion = jpype.JClass("dev.sentinel.guardian.Motion")
        policy = jpype.JClass("dev.sentinel.guardian.NumericPolicy")
        frame = self.j["FrameId"](self.j["FrameKind"].LOCAL_WORLD, frame_id)
        vector = self.j["Vector3"]
        r = motion.relativePosition(vector(frame, *reference_position), vector(frame, *position))
        v = motion.relativeVelocity(vector(frame, *reference_velocity), vector(frame, *velocity))
        closing = motion.closingSpeed(r, v)
        ttc = motion.radialTtc(r, v)
        signed = motion.signedClosestApproachSeconds(r, v)
        cpa = motion.closestApproach(r, v)
        return RelativeMotionValues(
            float(r.magnitude()),
            float(closing.getAsDouble()) if closing.isPresent() else None,
            float(ttc.seconds().getAsDouble()) if ttc.isValid() else None,
            float(signed.getAsDouble()) if signed.isPresent() else None,
            float(cpa.distanceMeters().getAsDouble()) if cpa.isValid() else None,
            bool(v.magnitude() <= policy.NEAR_ZERO_SPEED_MPS),
        )

    def predict_world_points(
        self,
        frame_id: str,
        session_id: str,
        now: int,
        position: tuple[float, ...],
        velocity: tuple[float, ...],
        horizons: tuple[int, ...],
    ) -> tuple[tuple[float, ...], ...]:
        """Guardian nominal CV only; confidence zero, no physical validation/covariance."""
        vector_estimate = jpype.JClass("dev.sentinel.guardian.VectorEstimate")
        timed = jpype.JClass("dev.sentinel.guardian.TimedVectorEstimate")
        prediction = jpype.JClass("dev.sentinel.guardian.MotionPrediction")
        confidence = jpype.JClass("dev.sentinel.guardian.Confidence")(0.0)
        frame = self.j["FrameId"](self.j["FrameKind"].LOCAL_WORLD, frame_id)
        start = self.j["MonotonicTime"](session_id, now)

        def estimate(values: tuple[float, ...], quantity: Any) -> Any:
            return timed(
                start,
                vector_estimate(
                    frame,
                    quantity,
                    self.optional.of(self.j["Vector3"](frame, *values)),
                    self.optional.empty(),
                    confidence,
                ),
            )

        p = estimate(position, vector_estimate.Quantity.POSITION_METERS)
        v = estimate(velocity, vector_estimate.Quantity.VELOCITY_MPS)
        out = []
        for h in horizons:
            value = prediction.position(
                prediction.Model.CONSTANT_VELOCITY,
                p,
                self.optional.of(v),
                self.optional.empty(),
                self.j["MonotonicTime"](session_id, now + h),
                max(horizons),
            )
            if not value.isPresent():
                raise ValueError("Guardian prediction unavailable")
            out.append(CoreCorridor._tuple(value.get().estimate().value().get()))
        return tuple(out)

    def __init__(
        self,
        calibration: Calibration,
        jar: Path | None = None,
        source_scaling: Resolution | None = None,
    ) -> None:
        jar = jar or (
            Path(__file__).resolve().parents[4]
            / "packages/guardian-core/target/guardian-core-0.1.0.jar"
        )
        if not jar.is_file():
            raise LabError("BUILD_GUARDIAN_CORE_FIRST")
        if not jpype.isJVMStarted():
            jpype.startJVM(classpath=[str(jar)], convertStrings=True)
        self.c = calibration
        names = (
            "FrameId",
            "FrameKind",
            "ImageSize",
            "ImageTransform",
            "PixelPoint",
            "CameraIntrinsics",
            "CalibrationId",
            "CalibrationQuality",
            "CameraCalibration",
            "CameraModel",
            "GeometryPolicy",
            "NoDistortion",
            "BrownConradyDistortion",
            "Quaternion",
            "Vector3",
            "RigidTransform",
            "CameraExtrinsics",
            "MonotonicTime",
            "FrameMetadata",
            "WallClockTime",
        )
        self.j = {name: jpype.JClass("dev.sentinel.guardian." + name) for name in names}
        self.optional = jpype.JClass("java.util.Optional")
        self.optional_double = jpype.JClass("java.util.OptionalDouble")
        self.optional_long = jpype.JClass("java.util.OptionalLong")
        j = self.j
        self.camera = j["FrameId"](j["FrameKind"].CAMERA, calibration.camera_frame_id)
        self.image = j["FrameId"](j["FrameKind"].IMAGE, calibration.image_frame_id)
        r, k = calibration.resolution, calibration.intrinsics
        self.size = j["ImageSize"](self.image, r.width, r.height)
        intrinsics = j["CameraIntrinsics"](
            self.camera, self.image, r.width, r.height, k.fx, k.fy, k.cx, k.cy
        )
        self.calibration_id = j["CalibrationId"](
            calibration.camera_id, calibration.calibration_version
        )
        coefficients = calibration.distortion_coefficients
        distortion = (
            j["NoDistortion"]()
            if calibration.distortion_model == "none"
            else j["BrownConradyDistortion"](
                *[coefficients[key] for key in ("k1", "k2", "k3", "p1", "p2", "max_radius")]
            )
        )
        q = calibration.calibration_quality
        quality = j["CalibrationQuality"](
            getattr(j["CalibrationQuality"].State, q.state),
            self.optional_double.empty()
            if q.rms_pixels is None
            else self.optional_double.of(q.rms_pixels),
            self.optional_long.empty()
            if q.sample_count is None
            else self.optional_long.of(q.sample_count),
            self.optional.empty()
            if q.timestamp_epoch_millis is None
            else self.optional.of(j["WallClockTime"](q.timestamp_epoch_millis)),
        )
        self.model = j["CameraModel"](
            j["CameraCalibration"](
                self.calibration_id, intrinsics, distortion, quality, self.optional.empty()
            ),
            j["GeometryPolicy"].defaults(),
        )
        self.extrinsics = None
        if calibration.camera_to_device is not None:
            e = calibration.camera_to_device
            device = j["FrameId"](j["FrameKind"].DEVICE, e.device_frame_id)
            transform = j["RigidTransform"](
                self.camera,
                device,
                j["Quaternion"](*e.rotation_wxyz),
                j["Vector3"](device, *e.translation_meters),
            )
            self.extrinsics = j["CameraExtrinsics"](self.calibration_id, e.version, transform)
        self.calibration_size = self.size
        self.source_mapping: ImageMapping | None = None
        self.source_width, self.source_height = r.width, r.height
        if source_scaling is not None:
            self.source_width, self.source_height = source_scaling.width, source_scaling.height
            self.size = j["ImageSize"](
                j["FrameId"](j["FrameKind"].IMAGE, "lab-source-scaled"),
                self.source_width,
                self.source_height,
            )
            self.source_mapping = ImageMapping(
                j["ImageTransform"].scale(self.calibration_size, self.size), j["PixelPoint"]
            )

    def corridor(
        self,
        plane: "SuppliedGroundPlane",
        pose: "SuppliedDepthPose | None",
        config: "CorridorConfig",
        camera_heading: tuple[float, float, float] | None = None,
    ) -> CoreCorridor:
        """Call Guardian once per snapshot; all metric frame/plane arithmetic stays there."""
        j = self.j
        transform = None
        frame = self.camera
        if plane.coordinate_frame == "LOCAL_WORLD":
            if pose is None or self.extrinsics is None:
                raise ValueError("World corridor requires pose and extrinsics")
            frame = j["FrameId"](j["FrameKind"].LOCAL_WORLD, plane.frame_id)
            transform = self.extrinsics.cameraToDevice().then(
                j["RigidTransform"](
                    self.extrinsics.cameraToDevice().to(),
                    frame,
                    j["Quaternion"](*pose.rotation_wxyz),
                    j["Vector3"](frame, *pose.translation_meters),
                )
            )
        origin = j["Vector3"](self.camera, 0, 0, 0)
        forward = j["Vector3"](self.camera, *(camera_heading or (0.0, 0.0, 1.0)))
        if transform is not None:
            origin, forward = (
                transform.transformPoint(origin),
                transform.transformDirection(forward),
            )
        invalid_geometry = jpype.JClass("java.lang.IllegalArgumentException")
        try:
            core = jpype.JClass("dev.sentinel.guardian.CorridorGeometry").onPlane(
                origin,
                forward,
                j["Vector3"](frame, *plane.point_meters),
                j["Vector3"](frame, *plane.normal),
                config.near_m,
                config.far_m,
                config.near_half_width_m + config.expansion_m,
                config.far_half_width_m + config.expansion_m,
            )
        except invalid_geometry as error:
            raise ValueError("Guardian rejected degenerate corridor geometry") from error
        return CoreCorridor(core, transform, self)

    def roll_mapping(self, radians: float, canvas: str) -> ImageMapping:
        """Image-plane roll only; calibration remains in the original camera frame."""
        target = self.j["FrameId"](self.j["FrameKind"].IMAGE, "alpha-roll-canonical")
        transform = self.j["ImageTransform"].roll(self.size, target, radians, canvas)
        return ImageMapping(transform, self.j["PixelPoint"])

    def require_dimensions(self, width: int, height: int) -> None:
        if (width, height) != (self.source_width, self.source_height):
            raise LabError("CALIBRATION_RESOLUTION_MISMATCH")

    def mapping(
        self,
        operation: str,
        width: int,
        height: int,
        left: int = 0,
        top: int = 0,
        resized: tuple[int, int] | None = None,
    ) -> ImageMapping:
        j = self.j
        target = j["ImageSize"](j["FrameId"](j["FrameKind"].IMAGE, "lab-processed"), width, height)
        if operation in {"identity", "resize"}:
            transform = j["ImageTransform"].scale(self.size, target)
        elif operation == "crop":
            transform = j["ImageTransform"].crop(self.size, target, left, top)
        elif operation == "letterbox" and resized is not None:
            intermediate = j["ImageSize"](
                j["FrameId"](j["FrameKind"].IMAGE, "lab-resized"), *resized
            )
            transform = (
                j["ImageTransform"]
                .scale(self.size, intermediate)
                .then(j["ImageTransform"].pad(intermediate, target, left, top))
            )
        else:
            raise ValueError("Unsupported image operation")
        if self.source_mapping is not None:
            transform = j["ImageTransform"].scale(self.calibration_size, self.size).then(transform)
        return ImageMapping(transform, j["PixelPoint"])

    def metadata(self, identity: FrameIdentity) -> Any:
        """Bind source observation time, never the processing clock, to calibration."""
        j = self.j
        return j["FrameMetadata"](
            identity.sequence,
            self.image,
            j["MonotonicTime"](identity.source_id, identity.observation_ns),
            self.optional.empty(),
            self.c.resolution.width,
            self.c.resolution.height,
            self.optional.of(self.calibration_id),
        )

    def detection_to_core(self, detection: Detection, identity: FrameIdentity) -> Any:
        """Strict boundary: raw off-image/empty boxes need an explicit caller policy."""
        width, height = self.c.resolution.width, self.c.resolution.height
        b = detection.box
        normalized = jpype.JClass("dev.sentinel.guardian.BoundingBox2D")(
            b.x1 / width, b.y1 / height, b.x2 / width, b.y2 / height
        )
        return jpype.JClass("dev.sentinel.guardian.Detection2D")(
            "sentinel:" + detection.label.value,
            jpype.JClass("dev.sentinel.guardian.Confidence")(detection.confidence),
            normalized,
            self.metadata(identity),
        )

    def inspect(
        self, u: float, v: float, identity: FrameIdentity | None = None
    ) -> dict[str, object]:
        from .contracts import TimingProvenance

        j = self.j
        identity = identity or FrameIdentity("inspection", 0, 0, TimingProvenance.SYNTHETIC)
        metadata = self.metadata(identity)
        point = j["PixelPoint"](self.image, u, v)
        ray = self.model.pixelToCameraRay(point, metadata)
        bearing = self.model.bearing(point, metadata)
        if not ray.isPresent() or not bearing.isPresent():
            return {"available": False, "identity": asdict(identity)}
        vector, angles = ray.get(), bearing.get()
        return {
            "available": True,
            "identity": asdict(identity),
            "pixel": [u, v],
            "normalized_camera": [float(vector.x() / vector.z()), float(vector.y() / vector.z())],
            "camera_ray": [float(vector.x()), float(vector.y()), float(vector.z())],
            "horizontal_bearing_radians": float(angles.azimuthRadians()),
            "vertical_bearing_radians": float(angles.elevationRadians()),
            "quality": self.c.calibration_quality.state,
        }

    def bearing_angles(
        self, u: float, v: float, identity: FrameIdentity
    ) -> tuple[float, float] | None:
        """Typed Guardian angle boundary for compact world observations."""
        if self.c.calibration_quality.state not in {"VALID", "DEGRADED"}:
            return None
        bearing = self.model.bearing(
            self.j["PixelPoint"](self.image, u, v), self.metadata(identity)
        )
        if not bearing.isPresent():
            return None
        return float(bearing.get().azimuthRadians()), float(bearing.get().elevationRadians())

    def ground_candidate(
        self,
        pixel: tuple[float, float],
        identity: FrameIdentity,
        translation: tuple[float, float, float],
        rotation: tuple[float, float, float, float],
        world_id: str,
        plane_point: tuple[float, float, float],
        plane_normal: tuple[float, float, float],
    ) -> tuple[float, float, float] | None:
        """Exact-time supplied ground assumption; all transforms/intersection run in Java."""
        if self.extrinsics is None or self.c.calibration_quality.state not in {"VALID", "DEGRADED"}:
            return None
        j = self.j
        world = j["FrameId"](j["FrameKind"].LOCAL_WORLD, world_id)
        transform = j["RigidTransform"](
            self.extrinsics.cameraToDevice().to(),
            world,
            j["Quaternion"](*rotation),
            j["Vector3"](world, *translation),
        )
        time = j["MonotonicTime"](identity.source_id, identity.observation_ns)
        pose = jpype.JClass("dev.sentinel.guardian.DevicePoseEstimate")(
            time,
            self.optional.of(transform),
            jpype.JClass("dev.sentinel.guardian.Confidence")(0),
            self.optional_double.empty(),
            self.optional_double.empty(),
        )
        spatial = jpype.JClass("dev.sentinel.guardian.SpatialGeometry")
        ray = spatial.pixelToWorldRay(
            j["PixelPoint"](self.image, *pixel),
            self.metadata(identity),
            self.model,
            self.extrinsics,
            pose,
        )
        if not ray.isPresent():
            return None
        plane = jpype.JClass("dev.sentinel.guardian.Plane3D")(
            j["Vector3"](world, *plane_point), j["Vector3"](world, *plane_normal)
        )
        ground = jpype.JClass("dev.sentinel.guardian.GroundPlaneEstimate")(
            self.optional.of(plane),
            time,
            jpype.JClass("dev.sentinel.guardian.Confidence")(0),
            self.optional_double.empty(),
            self.optional_double.empty(),
            "SUPPLIED_ASSUMPTION",
        )
        point = spatial.groundIntersection(
            ray.get(), ground, jpype.JClass("dev.sentinel.guardian.GeometryPolicy").defaults()
        )
        if not point.isPresent():
            return None
        value = point.get().nominalPoint()
        return float(value.x()), float(value.y()), float(value.z())

    def depth_point(
        self, u: float, v: float, meters: float, camera_z: bool, identity: FrameIdentity
    ) -> tuple[float, float, float] | None:
        """Scale Guardian's calibrated unit ray using explicit Z versus ray range."""
        from math import isfinite

        if not isfinite(meters) or meters <= 0:
            raise ValueError("Positive finite metric depth required")
        ray = self.model.pixelToCameraRay(
            self.j["PixelPoint"](self.image, u, v), self.metadata(identity)
        )
        if not ray.isPresent():
            return None
        vector = ray.get()
        if camera_z and float(vector.z()) <= 0:
            return None
        point = vector.multiply(meters / float(vector.z()) if camera_z else meters)
        return float(point.x()), float(point.y()), float(point.z())

    def depth_world_point(
        self,
        point: tuple[float, float, float],
        identity: FrameIdentity,
        pose_identity: FrameIdentity,
        translation: tuple[float, float, float],
        rotation_wxyz: tuple[float, float, float, float],
        world_id: str,
    ) -> tuple[float, float, float] | None:
        """Caller supplies exact-frame pose; Java validates frames and composes transforms."""
        if pose_identity != identity:
            raise ValueError("Depth/pose identity mismatch")
        if self.extrinsics is None:
            return None
        j = self.j
        camera_device = self.extrinsics.cameraToDevice()
        world = j["FrameId"](j["FrameKind"].LOCAL_WORLD, world_id)
        device_world = j["RigidTransform"](
            camera_device.to(),
            world,
            j["Quaternion"](*rotation_wxyz),
            j["Vector3"](world, *translation),
        )
        pose = jpype.JClass("dev.sentinel.guardian.DevicePoseEstimate")(
            j["MonotonicTime"](identity.source_id, identity.observation_ns),
            self.optional.of(device_world),
            jpype.JClass("dev.sentinel.guardian.Confidence")(0.0),
            self.optional_double.empty(),
            self.optional_double.empty(),
        )
        output = camera_device.then(pose.transform().get()).transformPoint(
            j["Vector3"](self.camera, *point)
        )
        return float(output.x()), float(output.y()), float(output.z())


class MotionPoseHistory:
    """Typed Task004 bridge: bounded exact/interpolated DEVICE->WORLD poses."""

    def __init__(
        self, geometry: CoreGeometry, session_id: str, world_id: str, max_span_ns: int = 100_000_000
    ) -> None:
        if geometry.extrinsics is None or not session_id or not 0 < max_span_ns <= 1_000_000_000:
            raise ValueError("Explicit extrinsics/session/alignment policy required")
        self.g, self.session_id = geometry, session_id
        self.history = jpype.JClass("dev.sentinel.guardian.PoseHistory")(256, 5_000_000_000, 0)
        self.policy = jpype.JClass("dev.sentinel.guardian.SynchronizationPolicy")(
            max_span_ns, 0, False, False
        )
        self.world = geometry.j["FrameId"](geometry.j["FrameKind"].LOCAL_WORLD, world_id)

    def add(
        self,
        session_id: str,
        identity: FrameIdentity,
        device_to_world_wxyz: tuple[float, float, float, float],
    ) -> None:
        if session_id != self.session_id or identity.timing.value == "UNKNOWN":
            raise ValueError("Pose session mismatch")
        g = self.g
        assert g.extrinsics is not None
        transform = g.j["RigidTransform"](
            g.extrinsics.cameraToDevice().to(),
            self.world,
            g.j["Quaternion"](*device_to_world_wxyz),
            g.j["Vector3"](self.world, 0, 0, 0),
        )
        pose = jpype.JClass("dev.sentinel.guardian.DevicePoseEstimate")(
            g.j["MonotonicTime"](identity.source_id, identity.observation_ns),
            g.optional.of(transform),
            jpype.JClass("dev.sentinel.guardian.Confidence")(0),
            g.optional_double.empty(),
            g.optional_double.empty(),
        )
        status = str(self.history.add(pose))
        if status != "ACCEPTED":
            raise ValueError("Pose insertion rejected")

    def relative_rotation(
        self, session_id: str, a: FrameIdentity, b: FrameIdentity
    ) -> NDArray[np.float64] | None:
        if (
            session_id != self.session_id
            or a.source_id != b.source_id
            or a.timing != b.timing
            or a.timing.value == "UNKNOWN"
            or b.sequence <= a.sequence
            or b.observation_ns <= a.observation_ns
        ):
            raise ValueError("Pose pair mismatch")
        g = self.g
        assert g.extrinsics is not None
        poses = [
            self.history.at(g.j["MonotonicTime"](i.source_id, i.observation_ns), self.policy)
            for i in (a, b)
        ]
        if any(str(p.mode()) not in {"EXACT", "INTERPOLATED"} for p in poses):
            return None
        # Camera A -> world -> camera B, through Java's frame-checked transforms.
        ca = g.extrinsics.cameraToDevice().then(poses[0].value().get().transform().get())
        cb = g.extrinsics.cameraToDevice().then(poses[1].value().get().transform().get())
        relative = ca.then(cb.inverse())
        columns = []
        for xyz in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            v = relative.transformDirection(g.j["Vector3"](g.camera, *xyz))
            columns.append([float(v.x()), float(v.y()), float(v.z())])
        return np.array(columns, dtype=np.float64).T
