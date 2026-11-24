from dataclasses import replace

import numpy as np
import pytest

from perception_lab.config import Calibration
from perception_lab.contracts import ComponentProvenance, FrameIdentity, TimingProvenance
from perception_lab.depth import (
    DepthAxis,
    DepthDirection,
    DepthFrame,
    DepthKind,
    DepthRepresentation,
)
from perception_lab.ego_runtime import DepthAssistedEgoEstimator, VisualEgoEstimator
from perception_lab.flow import DenseFlowField, FramePair, SparseFlowObservation, restore_points
from perception_lab.flow_runtime import ClassicalFlowProvider, FlowAdapter
from perception_lab.geometry import CoreGeometry, MotionPoseHistory
from perception_lab.motion import CameraMotionEstimate, MotionQuality, ScaleStatus, sample_tracks
from perception_lab.motion_config import MotionConfig
from perception_lab.motion_geometry import calibration_hash, compensate, project
from perception_lab.motion_imu import ImuRotationEstimator, rotation_disagreement
from perception_lab.motion_masking import dynamic_exclusions

PROVENANCE = ComponentProvenance("synthetic", "optical_flow")


@pytest.fixture
def camera(calibration):
    raw = calibration.model_dump()
    raw.update(
        calibration_quality={
            "state": "VALID",
            "rms_pixels": 0.0,
            "sample_count": 160,
            "timestamp_epoch_millis": None,
        },
        resolution={"width": 640, "height": 480},
        intrinsics={"fx": 500.0, "fy": 500.0, "cx": 320.0, "cy": 240.0, "skew": 0},
    )
    return CoreGeometry(Calibration.model_validate(raw))


def pair(g, dt=100_000_000):
    return FramePair(
        "session",
        FrameIdentity("clock", 0, 0, TimingProvenance.SYNTHETIC),
        FrameIdentity("clock", 1, dt, TimingProvenance.SYNTHETIC),
        calibration_hash(g),
        g.c.image_frame_id,
        640,
        480,
    )


def rotation_y(angle):
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def scene(g, rotation=None, translation=None):
    rng = np.random.default_rng(17)
    xy = rng.uniform([60, 50], [570, 430], (160, 2))
    z = rng.uniform(3, 12, (160, 1))
    xyz = np.column_stack(((xy - [320, 240]) / 500, np.ones(160))) * z
    rotation = np.eye(3) if rotation is None else rotation
    translation = np.zeros(3) if translation is None else translation
    target = project(g, xyz @ rotation.T + translation)
    return SparseFlowObservation(
        pair(g), xy, target, np.ones(160, dtype=np.bool_), np.zeros(160), PROVENANCE, 1, 2
    ), xyz


def estimate(flow, rotation, translation=None):
    return CameraMotionEstimate(
        flow.pair,
        rotation,
        None,
        ScaleStatus.DEPTH_SCALED_RESEARCH if translation is not None else ScaleStatus.NONE,
        MotionQuality("DEGRADED", "SYNTHETIC", 160, 160, 1, 1),
        PROVENANCE,
        1,
        2,
        translation,
        PROVENANCE if translation is not None else None,
    )


@pytest.mark.parametrize("change", ["reverse", "zero", "source", "timing", "gap"])
def test_pair_rejects_incompatible_time(camera, change):
    p = pair(camera)
    b = {
        "reverse": replace(p.b, observation_ns=0, sequence=0),
        "zero": replace(p.b, observation_ns=0),
        "source": replace(p.b, source_id="other"),
        "timing": replace(p.b, timing=TimingProvenance.UNKNOWN),
        "gap": replace(p.b, observation_ns=2_000_000_000),
    }[change]
    with pytest.raises(ValueError):
        replace(p, b=b)


def test_flow_immutable_and_variable_dt(camera):
    flow, _ = scene(camera, rotation_y(0.03))
    with pytest.raises(ValueError):
        flow.points_a.setflags(write=True)
    slow = replace(
        flow, pair=replace(flow.pair, b=replace(flow.pair.b, observation_ns=200_000_000))
    )
    assert np.allclose(
        flow.displacement / flow.pair.dt_seconds, 2 * slow.displacement / slow.pair.dt_seconds
    )


def test_resize_restores_vectors_not_only_positions(camera):
    mapping = camera.mapping("resize", 320, 240)
    a = np.array([[40.0, 50.0]])
    b = a + [10, 3]
    assert np.allclose(restore_points(mapping, b) - restore_points(mapping, a), [[20, 6]])
    crop = camera.mapping("crop", 320, 240, 20, 30)
    assert np.allclose(restore_points(crop, a), [[60, 80]])


@pytest.mark.parametrize("angle", [0, 0.03, -0.05])
def test_analytical_rotation_estimation_compensation(camera, angle):
    rotation = rotation_y(angle)
    flow, _ = scene(camera, rotation)
    motion = VisualEgoEstimator(camera, MotionConfig(ransac_pixels=0.2)).estimate(flow)
    assert motion.rotation is not None
    assert motion.translation_direction is None
    assert np.allclose(motion.rotation, rotation, atol=1e-7)
    residual = compensate(camera, flow, motion)
    assert residual.pair == flow.pair
    assert np.max(np.abs(residual.displacement[residual.valid])) < 1e-6


def test_essential_translation_direction_not_meters(camera):
    r, t = rotation_y(0.025), np.array([0.4, 0.03, 0.02])
    flow, _ = scene(camera, r, t)
    motion = VisualEgoEstimator(
        camera, MotionConfig(ransac_pixels=0.25, ransac_iterations=500)
    ).estimate(flow)
    assert motion.scale_status == ScaleStatus.UP_TO_SCALE
    assert motion.research_translation is None
    assert np.allclose(motion.rotation, r, atol=1e-3)
    assert np.dot(motion.translation_direction, t / np.linalg.norm(t)) > 0.99


def test_low_features_and_dynamic_exclusion_fail_closed(camera):
    flow, _ = scene(camera)
    visual = VisualEgoEstimator(camera, MotionConfig())
    assert visual.estimate(replace(flow, valid=np.zeros(160, dtype=np.bool_))).rotation is None
    result = visual.estimate(flow, np.ones(160, dtype=np.bool_))
    assert result.quality.reason == "DYNAMIC_SCENE_DOMINANT"
    assert result.rotation is None


def test_dynamic_outliers_rotation_remains_robust(camera):
    flow, _ = scene(camera, rotation_y(0.02))
    target = flow.points_b.copy()
    target[:15] += [40, -30]
    result = VisualEgoEstimator(camera, MotionConfig(ransac_pixels=0.3)).estimate(
        replace(flow, points_b=target)
    )
    assert np.allclose(result.rotation, rotation_y(0.02), atol=1e-6)


def depth_for(g, flow, xyz):
    values = np.ones((480, 640), dtype=np.float32) * 6
    for (u, v), point in zip(flow.points_a, xyz, strict=True):
        values[int(v), int(u)] = point[2]
    return DepthFrame(
        flow.pair.a,
        DepthRepresentation(DepthKind.METRIC, DepthDirection.LARGER_IS_FARTHER, DepthAxis.CAMERA_Z),
        values,
        np.ones(values.shape, dtype=np.bool_),
        g.mapping("identity", 640, 480),
        PROVENANCE,
        1,
        2,
    )


def test_depth_assisted_prediction_and_pnp(camera):
    r, t = rotation_y(0.02), np.array([0.2, 0, 0.01])
    flow, xyz = scene(camera, r, t)
    depth = depth_for(camera, flow, xyz)
    motion = DepthAssistedEgoEstimator(camera, MotionConfig(ransac_pixels=0.5), depth).estimate(
        flow
    )
    assert motion.scale_status == ScaleStatus.DEPTH_SCALED_RESEARCH
    assert np.allclose(motion.research_translation, t, atol=1e-4)
    residual = compensate(camera, flow, motion, depth)
    assert np.median(np.linalg.norm(residual.displacement[residual.valid], axis=1)) < 1e-3
    assert "UNVALIDATED_SCALE" in residual.compensation
    with pytest.raises(ValueError):
        compensate(camera, flow, motion)


@pytest.mark.parametrize("invalid", ["relative", "wrong_frame"])
def test_depth_cannot_supply_wrong_scale_or_frame(camera, invalid):
    flow, xyz = scene(camera)
    depth = depth_for(camera, flow, xyz)
    if invalid == "relative":
        depth = replace(
            depth,
            representation=DepthRepresentation(DepthKind.RELATIVE, DepthDirection.LARGER_IS_NEARER),
        )
    else:
        depth = replace(depth, identity=flow.pair.b)
    with pytest.raises(ValueError):
        DepthAssistedEgoEstimator(camera, MotionConfig(), depth).estimate(flow)


def test_calibration_and_session_mismatch(camera):
    flow, _ = scene(camera)
    with pytest.raises(ValueError):
        VisualEgoEstimator(camera, MotionConfig()).estimate(
            replace(flow, pair=replace(flow.pair, calibration_hash="wrong"))
        )
    with pytest.raises(ValueError):
        compensate(
            camera,
            flow,
            replace(estimate(flow, np.eye(3)), pair=replace(flow.pair, session_id="other")),
        )


@pytest.mark.parametrize("provider", ["lk", "dis"])
def test_real_cpu_flow_translation_and_reversal(camera, provider):
    rng = np.random.default_rng(44)
    a = rng.integers(0, 256, (240, 320), dtype=np.uint8)
    b = np.roll(a, 3, axis=1)
    runtime = ClassicalFlowProvider(MotionConfig(flow_provider=provider))
    mapping = camera.mapping("resize", 320, 240)
    forward = runtime.estimate(a, b, pair(camera), mapping)
    reverse = runtime.estimate(b, a, pair(camera), mapping)
    if isinstance(forward, DenseFlowField):
        forward, reverse = forward.sparse(), reverse.sparse()
    assert forward.valid.sum() > 30
    assert np.median(forward.displacement[forward.valid], axis=0) == pytest.approx([6, 0], abs=0.4)
    assert np.median(reverse.displacement[reverse.valid], axis=0) == pytest.approx([-6, 0], abs=0.4)


def test_imu_mount_rotation_and_missing_alignment(camera):
    raw = camera.c.model_dump()
    q = np.sqrt(0.5)
    raw["camera_to_device"] = {
        "version": "mount",
        "device_frame_id": "device",
        "rotation_wxyz": [q, 0.0, 0.0, q],
        "translation_meters": [0.0, 0.0, 0.0],
    }
    g = CoreGeometry(Calibration.model_validate(raw))
    flow, _ = scene(g)
    history = MotionPoseHistory(g, "session", "world")
    estimator = ImuRotationEstimator(history, PROVENANCE)
    assert estimator.estimate(flow).quality.reason == "IMU_UNAVAILABLE"
    history.add("session", flow.pair.a, (1, 0, 0, 0))
    angle = 0.1
    history.add("session", flow.pair.b, (np.cos(angle / 2), np.sin(angle / 2), 0, 0))
    motion = estimator.estimate(flow)
    # Mount maps camera Y to device -X; inverse device X rotation becomes camera +Y.
    assert np.allclose(motion.rotation, rotation_y(angle), atol=1e-8)
    assert rotation_disagreement(motion, motion) == pytest.approx(0, abs=1e-7)
    with pytest.raises(ValueError):
        history.relative_rotation("different", flow.pair.a, flow.pair.b)


def test_track_residual_sampling_and_predicted_exclusion(camera):
    from perception_lab.detection import Box, ObjectClass
    from perception_lab.tracking_types import (
        DetectorEvidence,
        Lifecycle,
        TrackId,
        TrackSet,
        TrackSnapshot,
    )

    flow, _ = scene(camera, rotation_y(0.03))
    residual = compensate(camera, flow, estimate(flow, rotation_y(0.03)))
    box = Box(0, 0, 640, 480)
    t = TrackSnapshot(
        TrackId("session", 42),
        Lifecycle.CONFIRMED,
        "OBSERVED",
        ObjectClass.CAR,
        0.9,
        box,
        box,
        box,
        flow.pair.b.observation_ns,
        flow.pair.b.observation_ns,
        0,
        0,
        1,
        0,
        1,
        0,
        0.9,
        0.9,
        (0.0, 0.0),
        0,
        (),
        PROVENANCE,
        None,
    )
    tracks = TrackSet("session", flow.pair.b, (t,), (), DetectorEvidence.SUCCESS, (), PROVENANCE)
    obs = sample_tracks(tracks, residual)
    assert obs[0].track_id.serial == 42
    assert np.linalg.norm(obs[0].median_displacement_pixels) < 1e-6
    assert (
        sample_tracks(
            replace(tracks, tracks=(replace(t, observation_status="PREDICTED"),)), residual
        )
        == ()
    )
    assert dynamic_exclusions(flow, tracks=tracks).all()
    assert not dynamic_exclusions(flow).any()


def test_flow_adapter_gap_and_close(camera):
    from perception_lab.config import PreprocessConfig
    from perception_lab.contracts import Frame, PixelFormat
    from perception_lab.preprocessing import BasicPreprocessor

    adapter = FlowAdapter(MotionConfig(), "session", calibration_hash(camera))
    p = pair(camera)
    pre = BasicPreprocessor(camera, PreprocessConfig())
    image = pre.prepare(Frame(p.a, np.zeros((480, 640, 3), dtype=np.uint8), PixelFormat.RGB, 0, 1))
    assert adapter.flow(image, p.a) is None
    assert adapter.flow(image, replace(p.b, observation_ns=2_000_000_000)) is None
    assert adapter.resets == 1
    adapter.close()
    assert adapter.previous is None


def test_pipeline_compact_recording(make_pipeline, geometry):
    from conftest import records

    from perception_lab.sources import SyntheticSource

    pipeline, recorder = make_pipeline(
        {
            "motion": {"estimator": "none"},
            "record_session": True,
            "intervals_ns": {"optical_flow": 100_000_000},
        },
        motion_geometry=geometry,
    )
    pipeline.run(SyntheticSource(iter([0, 100_000_000, 200_000_000])))
    frames = [r for r in records(recorder) if r["type"] == "frame_result"]
    assert frames[1]["optical_flow"]["pair"]["a"]["observation_ns"] == 0
    assert "points_a" not in frames[1]["optical_flow"]
    assert recorder.manifest["schema_version"] == 4
    assert pipeline.flow.previous is None
    assert recorder.manifest["summary"]["flow_pairs_published"] == 2


def test_independent_object_residual_retained(camera):
    flow, _ = scene(camera, rotation_y(0.03))
    target = flow.points_b.copy()
    target[:20] += [7, -2]
    flow = replace(flow, points_b=target)
    residual = compensate(camera, flow, estimate(flow, rotation_y(0.03)))
    assert np.allclose(residual.displacement[:20], [7, -2], atol=1e-6)
    assert np.max(np.abs(residual.displacement[20:])) < 1e-6


def test_dense_ownership_bounded_conversion_and_no_retention(camera):
    import gc
    import weakref

    mapping = camera.mapping("resize", 64, 48)
    old = None
    for _ in range(2000):
        field = DenseFlowField(
            pair(camera),
            np.zeros((48, 64, 2)),
            np.ones((48, 64), dtype=np.bool_),
            np.zeros((48, 64)),
            mapping,
            PROVENANCE,
            1,
            2,
        )
        if old is not None:
            assert old() is None
        old = weakref.ref(field.vectors)
        sparse = field.sparse(40)
        assert len(sparse.valid) <= 40
        with pytest.raises(ValueError):
            field.vectors.setflags(write=True)
        del field
    gc.collect()
    assert old() is None


def test_degenerate_spatial_distribution(camera):
    flow, _ = scene(camera)
    points = flow.points_a.copy() / 20
    small = replace(flow, points_a=points, points_b=points)
    motion = VisualEgoEstimator(camera, MotionConfig()).estimate(small)
    assert motion.rotation is None
    assert motion.quality.reason == "POOR_SPATIAL_DISTRIBUTION"


def test_scale_contract_cannot_label_direction_as_metric(camera):
    flow, _ = scene(camera)
    motion = estimate(flow, np.eye(3))
    with pytest.raises(ValueError):
        replace(motion, translation_direction=np.array([1.0, 0, 0]))
    with pytest.raises(ValueError):
        replace(motion, scale_status=ScaleStatus.DEPTH_SCALED_RESEARCH)


def test_unavailable_motion_does_not_fabricate_zero_residual(camera):
    flow, _ = scene(camera)
    empty = replace(flow, valid=np.zeros(160, dtype=np.bool_))
    motion = VisualEgoEstimator(camera, MotionConfig()).estimate(empty)
    assert compensate(camera, empty, motion) is None


def test_depth_provider_swap_preserves_contract_but_changes_provenance(camera):
    flow, xyz = scene(camera, rotation_y(0.01), np.array([0.2, 0, 0]))
    depth = depth_for(camera, flow, xyz)
    other = replace(depth, provenance=ComponentProvenance("alternative-depth", "depth"))
    results = [
        DepthAssistedEgoEstimator(camera, MotionConfig(), d).estimate(flow) for d in (depth, other)
    ]
    assert results[0].scale_source != results[1].scale_source
    assert np.allclose(results[0].research_translation, results[1].research_translation)
    assert results[0].pair == results[1].pair


def test_detector_swap_and_semantic_extension(camera):
    from perception_lab.detection import Box, Detection, DetectionBatch, ObjectClass

    flow, _ = scene(camera)
    detection = Detection(2, "car", ObjectClass.CAR, 0.8, Box(0, 0, 320, 480))
    masks = []
    for name in ("PicoDet-S", "YOLOX-Nano"):
        batch = DetectionBatch(
            flow.pair.b, (detection,), ComponentProvenance(name, "detector"), "a" * 64, 1, 2
        )
        masks.append(dynamic_exclusions(flow, batch))
    assert np.array_equal(*masks)
    assert masks[0].any() and not masks[0].all()

    class FutureSemantic:
        def excluded(self, identity, points):
            assert identity == flow.pair.b
            return points[:, 0] < 320

    assert np.array_equal(dynamic_exclusions(flow, semantic=FutureSemantic()), masks[0])


def test_visual_replay_deterministic(camera):
    flow, _ = scene(camera, rotation_y(0.025), np.array([0.4, 0.03, 0.02]))
    estimator = VisualEgoEstimator(camera, MotionConfig(ransac_pixels=0.25))
    a, b = estimator.estimate(flow), estimator.estimate(flow)
    assert a.quality == b.quality
    assert np.allclose(a.rotation, b.rotation)


def test_depth_translation_near_points_have_larger_parallax(camera):
    flow, xyz = scene(camera, translation=np.array([0.2, 0, 0]))
    depth = depth_for(camera, flow, xyz)
    residual = compensate(camera, flow, estimate(flow, np.eye(3), np.array([0.2, 0, 0])), depth)
    assert np.max(np.abs(residual.displacement)) < 1e-5
    magnitudes = np.linalg.norm(residual.expected_displacement, axis=1)
    assert np.median(magnitudes[xyz[:, 2] < 5]) > np.median(magnitudes[xyz[:, 2] > 10])


def test_distortion_is_removed_before_visual_geometry(camera):
    raw = camera.c.model_dump()
    raw.update(
        distortion_model="brown_conrady",
        distortion_coefficients={
            "k1": 0.05,
            "k2": -0.01,
            "k3": 0.0,
            "p1": 0.001,
            "p2": -0.001,
            "max_radius": 2.0,
        },
    )
    g = CoreGeometry(Calibration.model_validate(raw))
    base, xyz = scene(camera)
    rotation = rotation_y(0.02)
    flow = replace(
        base, pair=pair(g), points_a=project(g, xyz), points_b=project(g, xyz @ rotation.T)
    )
    result = VisualEgoEstimator(g, MotionConfig(ransac_pixels=0.2)).estimate(flow)
    assert np.allclose(result.rotation, rotation, atol=1e-6)
    residual = compensate(g, flow, result)
    assert np.max(np.abs(residual.displacement[residual.valid])) < 1e-4


def test_provider_rejects_wrong_mapping_dimensions(camera):
    provider = ClassicalFlowProvider(MotionConfig())
    image = np.zeros((240, 320), dtype=np.uint8)
    with pytest.raises(ValueError, match="mapping"):
        provider.estimate(image, image, pair(camera), camera.mapping("identity", 640, 480))


def test_flow_provider_swap_same_motion_consumer(camera):
    from perception_lab.flow_synthetic import SyntheticFlowProvider

    rng = np.random.default_rng(5)
    image = rng.integers(0, 256, (240, 320), dtype=np.uint8)
    mapping = camera.mapping("resize", 320, 240)
    estimator = VisualEgoEstimator(camera, MotionConfig())
    providers = [
        SyntheticFlowProvider(),
        ClassicalFlowProvider(MotionConfig()),
        ClassicalFlowProvider(MotionConfig(flow_provider="dis")),
    ]
    for provider in providers:
        flow = provider.estimate(image, image, pair(camera), mapping)
        sparse = flow.sparse() if isinstance(flow, DenseFlowField) else flow
        result = estimator.estimate(sparse)
        assert np.allclose(result.rotation, np.eye(3), atol=1e-5)
        assert result.pair == flow.pair


def test_unknown_calibration_cannot_produce_camera_motion(camera):
    raw = camera.c.model_dump()
    raw["calibration_quality"]["state"] = "UNKNOWN"
    unknown = CoreGeometry(Calibration.model_validate(raw))
    flow, xyz = scene(unknown)
    assert (
        VisualEgoEstimator(unknown, MotionConfig()).estimate(flow).quality.reason
        == "CALIBRATION_UNAVAILABLE"
    )
    depth = depth_for(unknown, flow, xyz)
    assert DepthAssistedEgoEstimator(unknown, MotionConfig(), depth).estimate(flow).rotation is None
