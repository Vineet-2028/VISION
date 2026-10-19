from dataclasses import replace

import numpy as np
import pytest
from conftest import records
from test_tracking_pipeline import FixtureDetector

from perception_lab.contracts import ComponentProvenance, FrameIdentity, TimingProvenance
from perception_lab.depth import (
    DepthAxis,
    DepthDirection,
    DepthFrame,
    DepthKind,
    DepthRepresentation,
)
from perception_lab.depth_sampling import (
    SamplingPolicy,
    detection_depth,
    sample_pixel,
    sample_region,
    track_depth,
)
from perception_lab.depth_spatial import camera_point
from perception_lab.depth_synthetic import SyntheticDepthProvider
from perception_lab.geometry import CoreGeometry
from perception_lab.preprocessing import BasicPreprocessor
from perception_lab.sources import SyntheticSource


@pytest.fixture
def plane(geometry):
    return DepthFrame(
        FrameIdentity("synthetic", 0, 0, TimingProvenance.SYNTHETIC),
        DepthRepresentation(DepthKind.METRIC, DepthDirection.LARGER_IS_FARTHER, DepthAxis.CAMERA_Z),
        np.full((6, 8), 5, dtype=np.float32),
        np.ones((6, 8), dtype=np.bool_),
        geometry.mapping("identity", 8, 6),
        ComponentProvenance("fixture", "depth"),
        0,
        1,
    )


def test_map_ownership_and_nonfinite_mask(plane):
    source = np.array(plane.values)
    source[0, :4] = [np.nan, np.inf, -1, 0]
    frame = replace(plane, values=source)
    source[:] = 100
    assert not frame.valid[0, :4].any()
    assert sample_pixel(frame, 4.5, 0.5) == 5
    assert sample_pixel(frame, 0.5, 0.5) is None
    assert np.isfinite(frame.values).all()
    with pytest.raises(ValueError):
        frame.values.setflags(write=True)


@pytest.mark.parametrize("u,v", [(-1, 2), (8, 2), (1, 6), (float("nan"), 1)])
def test_sampling_does_not_extrapolate(plane, u, v):
    assert sample_pixel(plane, u, v) is None


def test_bilinear_gradient_and_invalid_neighbors(plane):
    frame = replace(plane, values=np.tile(np.arange(1, 9, dtype=np.float32), (6, 1)))
    assert sample_pixel(frame, 2, 2, "bilinear") == pytest.approx(2.5)
    assert sample_pixel(frame, 0, 2, "bilinear") is None
    mask = np.array(frame.valid)
    mask[1, 1] = False
    assert sample_pixel(replace(frame, valid=mask), 2, 2, "bilinear") is None


def test_region_statistics_and_relative_near_direction(plane):
    from perception_lab.detection import Box

    values = np.tile(np.arange(1, 9, dtype=np.float32), (6, 1))
    frame = replace(plane, values=values)
    estimate = sample_region(frame, Box(0, 0, 8, 6), SamplingPolicy(inset=0, grid=8))
    assert estimate.value == 4.5
    assert estimate.statistics.mad == 2
    relative = replace(
        frame,
        representation=DepthRepresentation(DepthKind.RELATIVE, DepthDirection.LARGER_IS_NEARER),
    )
    near = sample_region(
        relative, Box(0, 0, 8, 6), SamplingPolicy(strategy="near_surface", inset=0, grid=8)
    )
    assert near.value == near.statistics.p75
    with pytest.raises(ValueError):
        _ = near.meters
    assert sample_region(frame, Box(-1, 0, 8, 6)) is None


def test_off_axis_z_is_not_range(plane, geometry):
    from perception_lab.detection import Box

    estimate = sample_region(plane, Box(6, 2, 8, 4))
    point = camera_point(estimate, geometry)
    assert point.position_meters == pytest.approx((1.875, 0, 5))
    range_estimate = replace(
        estimate, representation=replace(estimate.representation, axis=DepthAxis.RAY_RANGE)
    )
    range_point = camera_point(range_estimate, geometry)
    assert np.linalg.norm(range_point.position_meters) == pytest.approx(5)
    assert range_point.position_meters[2] < 5


def test_world_transform_uses_exact_pose_and_java(plane, calibration):
    from perception_lab.config import Extrinsics

    geometry = CoreGeometry(calibration.model_copy(update={"camera_to_device": None}))
    assert (
        geometry.depth_world_point(
            (0, 0, 5), plane.identity, plane.identity, (1, 2, 3), (1, 0, 0, 0), "world"
        )
        is None
    )
    with pytest.raises(ValueError, match="identity"):
        geometry.depth_world_point(
            (0, 0, 5),
            plane.identity,
            replace(plane.identity, sequence=1),
            (1, 2, 3),
            (1, 0, 0, 0),
            "world",
        )
    extrinsics = Extrinsics(
        version="test",
        device_frame_id="body",
        rotation_wxyz=[1.0, 0.0, 0.0, 0.0],
        translation_meters=[1.0, 0.0, 0.0],
    )
    calibrated = CoreGeometry(calibration.model_copy(update={"camera_to_device": extrinsics}))
    assert calibrated.depth_world_point(
        (0, 0, 5), plane.identity, plane.identity, (1, 2, 3), (1, 0, 0, 0), "world"
    ) == pytest.approx((2, 2, 8))


@pytest.mark.parametrize("value", [5.0, 10.0])
def test_provider_swap_and_pipeline_async_semantics(make_pipeline, value):
    pipeline, recorder = make_pipeline(
        {
            "record_session": True,
            "intervals_ns": {"detector": 10, "depth": 20},
            "detector": {"weights": "unused.pt", "sha256": "a" * 64, "confidence": 0.1},
            "tracker": {"minimum_hits": 2},
        },
        detector=FixtureDetector(),
        depth=SyntheticDepthProvider(value),
    )
    pipeline.run(SyntheticSource(iter([0, 10, 20, 25])))
    frames = [r for r in records(recorder) if r["type"] == "frame_result"]
    assert frames[0]["detection_depths"][0]["value"] == value
    assert frames[1]["depth"] is None
    assert frames[1]["track_depths"][0]["observation_status"] == "UNAVAILABLE"
    assert frames[2]["track_depths"][0]["estimate"]["value"] == value
    assert frames[3]["track_depths"][0]["estimate"] is None
    assert "values" not in frames[0]["depth"]
    assert "valid" not in frames[0]["depth"]
    assert recorder.manifest["schema_version"] == 3


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_id", "other"),
        ("sequence", 1),
        ("observation_ns", 1),
        ("timing", TimingProvenance.AUTHORITATIVE_PTS),
    ],
)
def test_detection_identity_mismatch_rejected(plane, geometry, config, field, value):
    prepared = BasicPreprocessor(geometry, config.preprocess).prepare(
        next(iter(SyntheticSource(iter([0]))))
    )
    batch = FixtureDetector().detect(prepared, replace(plane.identity, **{field: value}))
    with pytest.raises(ValueError, match="identity"):
        detection_depth(batch, plane)


def test_predicted_track_with_current_map_is_unavailable(plane, geometry, config):
    from perception_lab.tracking import AssociationTracker
    from perception_lab.tracking_config import TrackerConfig
    from perception_lab.tracking_types import DetectorEvidence

    prepared = BasicPreprocessor(geometry, config.preprocess).prepare(
        next(iter(SyntheticSource(iter([0]))))
    )
    tracker = AssociationTracker(TrackerConfig(), "session", "synthetic", 8, 6)
    first = tracker.update(
        "session",
        plane.identity,
        DetectorEvidence.SUCCESS,
        FixtureDetector().detect(prepared, plane.identity),
    )
    assert track_depth(first, plane)[0].estimate is not None
    later = replace(plane.identity, sequence=1, observation_ns=100000000)
    predicted = tracker.update("session", later, DetectorEvidence.NO_DETECTOR_RUN)
    assert track_depth(predicted, replace(plane, identity=later))[0].estimate is None


def test_resize_and_crop_coordinates(plane, geometry):
    resized = replace(
        plane,
        values=np.full((3, 4), 7, dtype=np.float32),
        valid=np.ones((3, 4), dtype=np.bool_),
        mapping=geometry.mapping("resize", 4, 3),
    )
    assert sample_pixel(resized, 7.5, 5.5) == 7
    cropped = replace(
        plane,
        values=np.full((2, 2), 9, dtype=np.float32),
        valid=np.ones((2, 2), dtype=np.bool_),
        mapping=geometry.mapping("crop", 2, 2, 3, 2),
    )
    assert sample_pixel(cropped, 3.5, 2.5) == 9
    assert sample_pixel(cropped, 1.5, 2.5) is None


def test_depth_representation_and_range_rejected(plane):
    with pytest.raises(ValueError):
        DepthRepresentation(
            DepthKind.RELATIVE, DepthDirection.LARGER_IS_FARTHER, DepthAxis.CAMERA_Z
        )
    with pytest.raises(ValueError):
        DepthRepresentation(DepthKind.METRIC, DepthDirection.LARGER_IS_NEARER, DepthAxis.CAMERA_Z)
    limited = replace(plane, representation=replace(plane.representation, maximum=4.0))
    assert not limited.valid.any()


def test_long_synthetic_depth_releases_dense_maps(geometry, config):
    import gc
    import weakref

    provider = SyntheticDepthProvider()
    preprocessor = BasicPreprocessor(geometry, config.preprocess)
    references = []
    for frame in SyntheticSource(iter(range(2000))):
        depth = provider.estimate_depth(preprocessor.prepare(frame), frame.identity)
        if frame.identity.sequence % 100 == 0:
            references.append(weakref.ref(depth.values))
    del depth
    gc.collect()
    assert all(reference() is None for reference in references)


def test_track_id_change_does_not_transfer_depth(plane, geometry, config):
    from perception_lab.tracking import AssociationTracker
    from perception_lab.tracking_config import TrackerConfig
    from perception_lab.tracking_types import DetectorEvidence, TrackId

    prepared = BasicPreprocessor(geometry, config.preprocess).prepare(
        next(iter(SyntheticSource(iter([0]))))
    )
    tracker = AssociationTracker(TrackerConfig(), "session", "synthetic", 8, 6)
    first = tracker.update(
        "session",
        plane.identity,
        DetectorEvidence.SUCCESS,
        FixtureDetector().detect(prepared, plane.identity),
    )
    original = track_depth(first, plane)[0]
    alternate = replace(first, tracks=(replace(first.tracks[0], track_id=TrackId("session", 999)),))
    changed = track_depth(alternate, plane)[0]
    assert changed.track_id != original.track_id
    assert changed.estimate == original.estimate
    assert changed.estimate.identity == plane.identity


def test_config_depth_hashes_and_private_path(config):
    from perception_lab.config import LabConfig
    from perception_lab.depth_config import DepthConfig

    with pytest.raises(ValueError):
        DepthConfig(provider="dav2_relative")
    configured = LabConfig.model_validate(
        {**config.model_dump(), "depth": {"provider": "synthetic", "weights": "private"}}
    )
    assert "private" not in str(configured.public_configuration())


def test_realtime_catches_up_after_depth_slower_than_32_source_frames(make_pipeline, monkeypatch):
    from test_pipeline import SimulatedClock

    clock = SimulatedClock()
    monkeypatch.setattr("perception_lab.sources.processing_ns", clock)
    seen = []

    class SlowDepth(SyntheticDepthProvider):
        def estimate_depth(self, image, identity):
            seen.append(identity.sequence)
            clock.now += 100
            return super().estimate_depth(image, identity)

    pipeline, _ = make_pipeline(
        {
            "mode": "REALTIME",
            "drop_policy": "LATEST_FRAME",
            "queue_capacity": 1,
            "max_staleness_ns": 120,
            "intervals_ns": {"depth": 1},
        },
        depth=SlowDepth(),
        clock=clock,
        sleep=clock.sleep,
    )
    summary = pipeline.run(SyntheticSource(iter(range(350))))["summary"]
    assert seen[:3] == [0, 100, 200]
    assert summary["frame_counts"]["processed"] >= 3
    assert summary["peak_queue_depth"] == 1


def test_camera_point_rejects_other_calibration_image(plane, geometry):
    from perception_lab.detection import Box

    estimate = sample_region(plane, Box(2, 2, 4, 4))
    with pytest.raises(ValueError, match="calibration"):
        camera_point(replace(estimate, camera_image_id="another-camera-image"), geometry)
    with pytest.raises(ValueError, match="timing"):
        replace(plane, identity=replace(plane.identity, timing=TimingProvenance.UNKNOWN))


def test_end_to_end_typed_world_point(plane, calibration):
    from perception_lab.config import Extrinsics
    from perception_lab.depth_spatial import SuppliedDepthPose, world_point
    from perception_lab.detection import Box

    extrinsics = Extrinsics(
        version="test",
        device_frame_id="body",
        rotation_wxyz=[1.0, 0.0, 0.0, 0.0],
        translation_meters=[1.0, 0.0, 0.0],
    )
    geometry = CoreGeometry(calibration.model_copy(update={"camera_to_device": extrinsics}))
    estimate = sample_region(plane, Box(3, 2, 5, 4))
    camera = camera_point(estimate, geometry)
    pose = SuppliedDepthPose(plane.identity, "body", "local", (1, 2, 3), (1, 0, 0, 0))
    result = world_point(camera, geometry, pose)
    assert result.position_meters == pytest.approx((2, 2, 8))
    assert result.camera_point.depth == estimate
    assert world_point(camera, geometry, None) is None
    with pytest.raises(ValueError, match="identity"):
        world_point(
            camera,
            geometry,
            replace(pose, identity=replace(plane.identity, source_id="other-clock")),
        )
    with pytest.raises(ValueError, match="device"):
        world_point(camera, geometry, replace(pose, device_frame_id="other-device"))
