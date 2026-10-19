"""Analytical cross-task tests; synthetic geometry is never real-world evidence."""

from math import atan, sqrt

import jpype
import pytest

from perception_lab.config import PreprocessConfig
from perception_lab.contracts import ComponentProvenance, FrameIdentity, TimingProvenance
from perception_lab.detection import Box, Detection, DetectionBatch, ObjectClass
from perception_lab.preprocessing import BasicPreprocessor
from perception_lab.sources import SyntheticSource


def test_frame_preprocess_detection_core_ray_and_bearing(geometry):
    frame = next(iter(SyntheticSource(iter([123456789]))))
    prepared = BasicPreprocessor(
        geometry, PreprocessConfig(operation="letterbox", width=16, height=16)
    ).prepare(frame)
    # 8x6 -> 16x12 + top=2; source box(2,1,6,5) -> tensor(4,4,12,12).
    restored = prepared.mapping.restore_box(Box(4, 4, 12, 12))
    assert restored.coordinates == pytest.approx((2, 1, 6, 5))
    detection = Detection(0, "person", ObjectClass.PERSON, 0.9, restored)
    core = geometry.detection_to_core(detection, frame.identity)
    assert core.frame().captureTime().nanos() == frame.identity.observation_ns
    ray = geometry.model.groundContactRayCandidate(core).get()
    # Bottom center (4,5): (x,y,z)=(0, 1/4, 1), normalized.
    assert (ray.x(), ray.y(), ray.z()) == pytest.approx((0, 1 / sqrt(17), 4 / sqrt(17)))
    result = geometry.inspect(4, 5, frame.identity)
    assert result["pixel"] == [4, 5]
    assert result["horizontal_bearing_radians"] == 0
    assert result["vertical_bearing_radians"] == pytest.approx(-atan(0.25))
    assert result["identity"]["observation_ns"] == frame.identity.observation_ns


def test_capture_pose_interpolation_extrinsic_world_ray(geometry):
    def j(name):
        return jpype.JClass("dev.sentinel.guardian." + name)

    device = j("FrameId")(j("FrameKind").DEVICE, "body")
    world = j("FrameId")(j("FrameKind").LOCAL_WORLD, "world")
    identity = FrameIdentity("source-clock", 7, 500_000_000, TimingProvenance.SYNTHETIC)
    history = j("PoseHistory")(4, 2_000_000_000, 0)
    for nanos, x, q in ((0, 0, (1, 0, 0, 0)), (1_000_000_000, 2, (0, 0, 0, 1))):
        pose = j("DevicePoseEstimate")(
            j("MonotonicTime")("source-clock", nanos),
            geometry.optional.of(
                j("RigidTransform")(
                    device, world, j("Quaternion")(*q), j("Vector3")(world, x, 0, 0)
                )
            ),
            j("Confidence")(0.9),
            geometry.optional_double.empty(),
            geometry.optional_double.empty(),
        )
        history.add(pose)
    aligned = history.at(
        j("MonotonicTime")("source-clock", identity.observation_ns),
        j("SynchronizationPolicy")(1_000_000_000, 0, False, False),
    )
    assert str(aligned.mode()) == "INTERPOLATED"
    # Camera forward -> device forward via -90deg X; device yaw halfway -> +90deg Z.
    extrinsic = j("CameraExtrinsics")(
        geometry.calibration_id,
        "fixture",
        j("RigidTransform")(
            geometry.camera,
            device,
            j("Quaternion")(sqrt(0.5), -sqrt(0.5), 0, 0),
            j("Vector3")(device, 1, 0, 0),
        ),
    )
    ray = (
        j("SpatialGeometry")
        .pixelToWorldRay(
            j("PixelPoint")(geometry.image, 4, 3),
            geometry.metadata(identity),
            geometry.model,
            extrinsic,
            aligned.value().get(),
        )
        .get()
    )
    assert (ray.direction().x(), ray.direction().y(), ray.direction().z()) == pytest.approx(
        (-1, 0, 0), abs=1e-12
    )
    assert (ray.origin().x(), ray.origin().y(), ray.origin().z()) == pytest.approx((1, 1, 0))
    assert ray.time().get().nanos() == identity.observation_ns


def test_core_boundary_rejects_unclipped_out_of_image_box(geometry):
    identity = FrameIdentity("fixture", 1, 2, TimingProvenance.SYNTHETIC)
    with pytest.raises(Exception, match="normalized|nonnegative"):
        geometry.detection_to_core(
            Detection(0, "person", ObjectClass.PERSON, 0.9, Box(-1, 0, 4, 5)), identity
        )


@pytest.mark.parametrize("config_name,expected_sign", [("synthetic-a", -1), ("synthetic-b", 1)])
def test_configuration_selected_detector_swap_keeps_downstream_unchanged(
    geometry, config_name, expected_sign
):
    class SyntheticDetector:
        def __init__(self, box):
            self.box = box
            self.provenance = ComponentProvenance("synthetic", "detector")

        def detect(self, image, identity):
            detection = Detection(0, "person", ObjectClass.PERSON, 0.8, self.box)
            return DetectionBatch(
                identity, (detection,), self.provenance, image.mapping.fingerprint, 0, 0
            )

    factories = {
        "synthetic-a": lambda: SyntheticDetector(Box(0, 1, 2, 3)),
        "synthetic-b": lambda: SyntheticDetector(Box(6, 1, 8, 3)),
    }
    detector = factories[config_name]()
    frame = next(iter(SyntheticSource(iter([999]))))
    prepared = BasicPreprocessor(geometry, PreprocessConfig()).prepare(frame)
    batch = detector.detect(prepared, frame.identity)
    # Identical downstream code consumes only Sentinel types.
    core = geometry.detection_to_core(batch.detections[0], batch.identity)
    ray = geometry.model.groundContactRayCandidate(core).get()
    assert ray.x() * expected_sign > 0
    assert core.frame().captureTime().nanos() == 999
