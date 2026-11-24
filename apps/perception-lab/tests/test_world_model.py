import gc
import json
import weakref
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, asdict, replace

import numpy as np
import pytest
from conftest import records
from test_semantics import sample
from test_tracking_pipeline import FixtureDetector

from perception_lab.config import Calibration
from perception_lab.contracts import ComponentProvenance, FrameIdentity, TimingProvenance
from perception_lab.depth import (
    DepthAxis,
    DepthDirection,
    DepthFrame,
    DepthKind,
    DepthRepresentation,
)
from perception_lab.depth_sampling import track_depth
from perception_lab.depth_spatial import SuppliedDepthPose
from perception_lab.depth_synthetic import SyntheticDepthProvider
from perception_lab.detection import Box, ObjectClass
from perception_lab.flow import FramePair
from perception_lab.geometry import CoreGeometry
from perception_lab.motion import (
    CameraMotionEstimate,
    MotionQuality,
    ScaleStatus,
    TrackImageMotionObservation,
)
from perception_lab.semantic_runtime import SyntheticSegmenter
from perception_lab.semantics import ObservationStatus
from perception_lab.sources import SyntheticSource
from perception_lab.surfaces import SurfaceEvidenceExtractor
from perception_lab.tracking_types import (
    DetectorEvidence,
    Lifecycle,
    TrackId,
    TrackSet,
    TrackSnapshot,
)
from perception_lab.world_config import WorldModelConfig
from perception_lab.world_model import PrototypeWorldModel
from perception_lab.world_types import EntityLifecycle
from perception_lab.world_types import EvidenceStatus as S

P = ComponentProvenance("fixture", "tracker")


def identity(t=0, sequence=None):
    return FrameIdentity(
        "synthetic", t if sequence is None else sequence, t, TimingProvenance.SYNTHETIC
    )


def tracks(t=0, count=1, predicted=False, session="test", offset=0, observed=0):
    return TrackSet(
        session,
        identity(t),
        tuple(
            TrackSnapshot(
                track_id=TrackId(session, i + 1 + offset),
                lifecycle=Lifecycle.CONFIRMED,
                observation_status="PREDICTED" if predicted else "OBSERVED",
                category=ObjectClass.PERSON,
                category_confidence=0.9,
                bbox=Box(2, 1, 6, 5),
                predicted_bbox=Box(2, 1, 6, 5),
                latest_observed_bbox=Box(2, 1, 6, 5),
                latest_observed_ns=observed if predicted else t,
                state_ns=t,
                age_ns=t,
                observation_age_ns=t - observed if predicted else 0,
                hits=2,
                misses=0,
                consecutive_hits=2,
                consecutive_misses=0,
                observation_confidence=0.9,
                quality=0.8,
                image_velocity_pixels_per_second=(0.0, 0.0),
                uncertainty_proxy=0.0,
                history=(),
                detector_provenance=P,
                latest_failure=None,
            )
            for i in range(count)
        ),
        (),
        DetectorEvidence.NO_DETECTOR_RUN if predicted else DetectorEvidence.SUCCESS,
        (),
        P,
    )


def model(geometry=None, **config):
    return PrototypeWorldModel(WorldModelConfig(**config), "test", "synthetic", geometry)


@pytest.fixture
def spatial(calibration):
    data = calibration.model_dump()
    data["calibration_quality"] = {
        "state": "VALID",
        "rms_pixels": 0.0,
        "sample_count": 10,
        "timestamp_epoch_millis": None,
    }
    data["camera_to_device"] = {
        "version": "test",
        "device_frame_id": "device",
        "rotation_wxyz": [1.0, 0.0, 0.0, 0.0],
        "translation_meters": [1.0, 0.0, 0.0],
    }
    return CoreGeometry(Calibration.model_validate(data))


def depth(g, t=0, relative=False, name="depth-a"):
    representation = (
        DepthRepresentation(DepthKind.RELATIVE, DepthDirection.LARGER_IS_FARTHER, DepthAxis.NONE)
        if relative
        else DepthRepresentation(
            DepthKind.METRIC, DepthDirection.LARGER_IS_FARTHER, DepthAxis.CAMERA_Z
        )
    )
    return DepthFrame(
        identity(t),
        representation,
        np.full((6, 8), 5, np.float32),
        np.ones((6, 8), np.bool_),
        g.mapping("identity", 8, 6),
        ComponentProvenance(name, "depth"),
        0,
        1,
    )


def test_zero_inputs_and_immutable_snapshot():
    w = model()
    s = w.snapshot(0)
    assert not s.entities and s.surface_state.evidence.status == S.UNAVAILABLE
    assert all(c.status == S.UNAVAILABLE for c in s.capabilities)
    with pytest.raises(FrozenInstanceError):
        s.state_timestamp = 1
    assert json.loads(json.dumps(asdict(s)))["schema_version"] == 1


def test_analytical_cross_task_geometry_and_unverified_surface(spatial):
    w = model(spatial)
    ts = tracks()
    w.ingest_tracks(ts, 0)
    w.ingest_depth(track_depth(ts, depth(spatial))[0], 0)
    w.ingest_pose(
        "test",
        SuppliedDepthPose(
            identity(), "device", "local-world", (0.0, 2.0, 0.0), (1.0, 0.0, 0.0, 0.0)
        ),
        ComponentProvenance("pose", "pose"),
        0,
        "SYNTHETIC",
    )
    _, semantic = sample(spatial)
    w.ingest_semantic(semantic, 0)
    w.ingest_surface(SurfaceEvidenceExtractor().extract(semantic), 0)
    s = w.snapshot(0)
    e = s.entities[0]
    assert e.position_camera.position_meters == pytest.approx((0, 0, 5))
    assert e.position_world.position_meters == pytest.approx((1, 2, 5))
    assert e.position_world.identity == identity()
    assert e.depth_evidence.validation_status == "METRIC_DEPTH_UNVALIDATED"
    assert s.surface_state.validation_status == "UNVERIFIED"
    assert s.surface_state.flag_pixels and len(e.position_sources) == 2
    assert e.image_motion is None


def test_relative_never_becomes_metric(spatial):
    w = model(spatial)
    ts = tracks()
    w.ingest_tracks(ts, 0)
    w.ingest_depth(track_depth(ts, depth(spatial, relative=True))[0], 0)
    e = w.snapshot(0).entities[0]
    assert e.depth.representation.kind == DepthKind.RELATIVE
    assert e.position_camera is None and e.position_world is None
    assert e.depth_evidence.validation_status == "RELATIVE_ONLY"


def test_metric_estimate_capability_does_not_require_calibrated_position(geometry):
    w = model(geometry)
    ts = tracks()
    w.ingest_tracks(ts, 0)
    w.ingest_depth(track_depth(ts, depth(geometry))[0], 0)
    state = w.snapshot(0)
    capability = next(c for c in state.capabilities if c.name == "HAS_METRIC_DEPTH_ESTIMATE")
    assert capability.status == S.DEGRADED
    assert state.entities[0].position_camera is None
    assert state.entities[0].depth.value == 5


def test_async_stale_depth_and_source_times(spatial):
    w = model(spatial)
    ts = tracks()
    w.ingest_tracks(ts, 0)
    w.ingest_depth(track_depth(ts, depth(spatial))[0], 0)
    first = w.snapshot(0)
    w.ingest_tracks(tracks(100, predicted=True), 100)
    middle = w.snapshot(100).entities[0]
    assert middle.observation_status == "PREDICTED"
    assert middle.depth_evidence.status == S.STALE and middle.depth_evidence.age_ns == 100
    w.ingest_tracks(tracks(200), 200)
    last = w.snapshot(200).entities[0]
    assert last.observation_status == "OBSERVED" and last.depth_evidence.status == S.STALE
    assert last.depth.identity.observation_ns == 0
    assert first.entities[0].observation_status == "OBSERVED"


def test_stale_pose_never_substituted(spatial):
    w = model(spatial)
    w.ingest_pose(
        "test",
        SuppliedDepthPose(identity(), "device", "world", (0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)),
        P,
        0,
    )
    ts = tracks(10)
    w.ingest_tracks(ts, 10)
    w.ingest_depth(track_depth(ts, depth(spatial, 10))[0], 10)
    e = w.snapshot(10).entities[0]
    assert e.position_camera and e.position_world is None
    assert "POSE_DEPTH_TIME_MISMATCH" in e.reasons


@pytest.mark.parametrize("source", ["depth", "semantics", "detector", "pose", "motion"])
def test_failure_is_explicit_without_erasing_entity(source):
    w = model()
    w.ingest_tracks(tracks(), 0)
    w.ingest_tracks(tracks(10, predicted=True), 10)
    w.failure(source, "test", identity(10), 10)
    s = w.snapshot(10)
    assert len(s.entities) == 1 and s.entities[0].observation_status == "PREDICTED"
    assert next(x for x in s.subsystem_status if x.subsystem == source).status == S.FAILED


def test_wrong_session_rejected_without_mutation():
    w = model()
    with pytest.raises(ValueError):
        w.ingest_tracks(tracks(session="other"), 0)
    assert not w.snapshot(0).entities


@pytest.mark.parametrize("change", [dict(source_id="wrong"), dict(timing=TimingProvenance.UNKNOWN)])
def test_wrong_clock_rejected(change):
    w = model()
    with pytest.raises(ValueError):
        w.ingest_tracks(replace(tracks(), identity=replace(identity(), **change)), 0)


def test_future_and_backward_snapshot_rejected():
    w = model()
    with pytest.raises(ValueError):
        w.ingest_tracks(tracks(20), 10)
    w.ingest_tracks(tracks(20), 20)
    with pytest.raises(ValueError):
        w.snapshot(19)
    w.snapshot(20)
    with pytest.raises(ValueError):
        w.snapshot(0)


def test_duplicate_and_out_of_order_are_idempotent():
    w = model()
    w.ingest_tracks(tracks(), 0)
    w.ingest_tracks(tracks(20), 20)
    w.ingest_tracks(tracks(20), 20)
    w.ingest_tracks(tracks(10), 20)
    e = w.snapshot(20).entities[0]
    assert [h.identity.observation_ns for h in e.history] == [0, 20]
    assert w.created == 1


def test_late_window_rejects_independent_source(spatial):
    w = model(spatial, late_ns=10)
    w.ingest_tracks(tracks(), 0)
    w.ingest_pose(
        "test",
        SuppliedDepthPose(identity(), "device", "world", (0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)),
        P,
        20,
    )
    assert w.snapshot(20).camera_state.pose is None


def test_depth_wrong_frame_and_duplicate_do_not_update(spatial):
    w = model(spatial)
    ts = tracks()
    d = track_depth(ts, depth(spatial))[0]
    w.ingest_tracks(ts, 0)
    w.ingest_depth(d, 0)
    w.ingest_depth(d, 0)
    w.ingest_tracks(tracks(10), 10)
    w.ingest_depth(d, 10)
    e = w.snapshot(10).entities[0]
    assert e.depth_evidence.status == S.STALE
    with pytest.raises(ValueError):
        w.ingest_depth(replace(d, identity=identity(10)), 10)


def test_expiry_history_and_conservative_track_switch():
    w = model(history_count=2, fresh_ns=5, lost_ns=10, expire_ns=20)
    w.ingest_tracks(tracks(), 0)
    initial = w.snapshot(0).entities[0].entity_id
    w.ingest_tracks(tracks(1, offset=1), 1)
    s = w.snapshot(1)
    assert len(s.entities) == 2 and s.entities[1].entity_id != initial
    assert w.snapshot(11).entities[0].lifecycle == EntityLifecycle.LOST
    assert not w.snapshot(22).entities
    w.ingest_tracks(tracks(23), 23)
    assert w.snapshot(23).entities[0].entity_id.serial > initial.serial


@pytest.mark.parametrize("count", [1, 10, 50, 100, 129, 512])
def test_entity_ceiling_and_histories(count):
    w = model(history_count=2)
    for t in range(4):
        w.ingest_tracks(tracks(t, count), t)
    s = w.snapshot(3)
    assert len(s.entities) == min(128, count)
    assert all(len(e.history) == 2 for e in s.entities)
    if count > 128:
        assert "ENTITY_CAP_REACHED" in s.diagnostics
    assert len(s.diagnostics) <= 32


def test_reset_and_independent_sessions():
    a, b = model(), model()
    a.ingest_tracks(tracks(), 0)
    assert not b.snapshot(0).entities
    old = a.snapshot(0).entities[0].entity_id
    a.reset("test", "synthetic")
    a.ingest_tracks(tracks(), 0)
    assert a.snapshot(0).entities[0].entity_id != old
    a.close()
    with pytest.raises(ValueError):
        a.snapshot(1)


def test_single_writer_enforced():
    w = model()
    with ThreadPoolExecutor(1) as executor:
        with pytest.raises(ValueError, match="single-writer"):
            executor.submit(w.snapshot, 0).result()


def test_semantic_unverified_propagated_stale_and_dense_release(geometry):
    w = model(geometry)
    _, sem = sample(geometry)
    surface = SurfaceEvidenceExtractor().extract(sem)
    ref = weakref.ref(surface.evidence)
    w.ingest_semantic(sem, 0)
    w.ingest_surface(surface, 0)
    del surface
    gc.collect()
    assert ref() is None
    propagated = replace(
        sem, identity=identity(10), status=ObservationStatus.PROPAGATED, warp_count=1
    )
    w.ingest_semantic(propagated, 10)
    w.ingest_surface(SurfaceEvidenceExtractor().extract(propagated), 10)
    s = w.snapshot(10).surface_state
    assert s.evidence.status == S.PROPAGATED and s.evidence.age_ns == 10
    assert s.validation_status == "UNVERIFIED"
    s = w.snapshot(2_000_000_000).surface_state
    assert s.evidence.status == S.STALE and s.evidence.age_ns == 2_000_000_000
    assert not w.snapshot(6_000_000_000).surface_state.regions


@pytest.mark.parametrize("vendor", ["provider-a", "provider-b"])
def test_provider_swaps_preserve_world_contract(spatial, vendor):
    w = model(spatial)
    p = ComponentProvenance(vendor, "tracker")
    ts = replace(tracks(10), provenance=p)
    w.ingest_tracks(ts, 10)
    w.ingest_depth(track_depth(ts, depth(spatial, 10, name=vendor))[0], 10)
    pair = FramePair("test", identity(), identity(10), "cal", "synthetic-image", 8, 6)
    motion = CameraMotionEstimate(
        pair,
        np.eye(3),
        None,
        ScaleStatus.NONE,
        MotionQuality("DEGRADED", "RESEARCH", 10, 10, 1.0, 1.0),
        p,
        0,
        1,
    )
    w.ingest_camera_motion(motion, 10)
    m = TrackImageMotionObservation(
        TrackId("test", 1), pair, (1.0, 2.0), (1e8, 2e8), (0.0, 0.0), 5, 1.0, "ROTATION_ONLY"
    )
    w.ingest_image_motion(m, (p,), 10)
    _, sem = sample(spatial)
    sem = replace(sem, identity=identity(10), observed_identity=identity(10), provenance=p)
    w.ingest_semantic(sem, 10)
    w.ingest_surface(SurfaceEvidenceExtractor().extract(sem), 10)
    s = w.snapshot(10)
    assert s.entities[0].track_evidence.provenance[0] == p
    assert s.entities[0].depth.provenance.name == vendor
    assert s.entities[0].image_motion.median_rate_pixels_per_second == (1e8, 2e8)
    assert s.surface_state.validation_status == "UNVERIFIED"
    assert "physical_velocity" not in asdict(s.entities[0])


def test_deterministic_world_sequence():
    def run():
        w = model()
        out = []
        for t in range(20):
            w.ingest_tracks(tracks(t, predicted=t % 2 == 1, observed=max(0, t - 1)), t)
            out.append(asdict(w.snapshot(t)))
        return out

    assert run() == run()


def test_full_pipeline_recording_and_failures(make_pipeline, geometry):
    p, r = make_pipeline(
        {
            "world_model": {},
            "record_session": True,
            "intervals_ns": {
                "detector": 100_000_000,
                "depth": 100_000_000,
                "segmentation": 100_000_000,
            },
            "detector": {"weights": "unused", "sha256": "a" * 64, "confidence": 0.1},
            "tracker": {"minimum_hits": 2},
        },
        detector=FixtureDetector(True),
        depth=SyntheticDepthProvider(),
        motion_geometry=geometry,
    )
    p.segmentation = SyntheticSegmenter(r.session_id)
    p.run(SyntheticSource(iter([0, 100_000_000, 150_000_000, 200_000_000])))
    rows = [x for x in records(r) if x["type"] == "frame_result"]
    assert r.manifest["schema_version"] == 6
    assert all(x["world_state"]["schema_version"] == 1 for x in rows)
    assert rows[-1]["world_state"]["entities"][0]["observation_status"] == "PREDICTED"
    assert rows[0]["world_state"]["surface_state"]["validation_status"] == "UNVERIFIED"
    assert p.world_model._closed
    assert not p.world_model._entities


@pytest.mark.parametrize(
    "options", [{}, {"tracker": {"minimum_hits": 2}}, {"depth": {"provider": "synthetic"}}]
)
def test_partial_pipeline(make_pipeline, options):
    changes = {"world_model": {}, **options}
    if "tracker" in options:
        changes["detector"] = {"weights": "unused", "sha256": "a" * 64}
    p, r = make_pipeline(changes, detector=FixtureDetector(), depth=SyntheticDepthProvider())
    p.run(SyntheticSource(iter([0, 10, 20])))
    assert r.manifest["summary"]["world_states_published"] == 3
    assert r.manifest["summary"]["frame_counts"]["failed"] == 0


def test_surface_failure_keeps_original_time_and_expires(geometry):
    w = model(geometry)
    _, semantic = sample(geometry)
    w.ingest_surface(SurfaceEvidenceExtractor().extract(semantic), 0)
    w.failure("surface", "test", identity(100), 100)
    s = w.snapshot(100).surface_state
    assert s.evidence.identity.observation_ns == 0
    assert s.evidence.age_ns == 100 and s.evidence.status == S.FAILED
    w.failure("surface", "test", identity(6_000_000_000), 6_000_000_000)
    assert not w.snapshot(6_000_000_000).surface_state.regions


def test_camera_motion_failure_does_not_retimestamp_payload():
    w = model()
    pair = FramePair("test", identity(), identity(10), "cal", "image", 8, 6)
    m = CameraMotionEstimate(
        pair,
        np.eye(3),
        None,
        ScaleStatus.NONE,
        MotionQuality("DEGRADED", "RESEARCH", 10, 10, 1.0, 1.0),
        P,
        0,
        1,
    )
    w.ingest_camera_motion(m, 10)
    w.failure("motion", "test", identity(20), 20)
    camera = w.snapshot(20).camera_state
    assert camera.motion_evidence.identity == pair.b
    assert camera.motion_evidence.age_ns == 10 and camera.motion_evidence.status == S.FAILED


def test_unverified_semantics_never_override_category(geometry):
    w = model(geometry)
    w.ingest_tracks(tracks(), 0)
    _, sem = sample(geometry, "sidewalk")
    w.ingest_semantic(sem, 0)
    state = w.snapshot(0)
    assert state.entities[0].category == ObjectClass.PERSON
    assert state.entities[0].semantic_center_label == "SIDEWALK"
    assert state.entities[0].semantic_evidence.validation_status == "UNVERIFIED"
    assert "SEMANTIC_CENTER_CATEGORY_DISAGREEMENT_UNVERIFIED" in state.diagnostics


def test_history_carries_observed_depth_not_prediction(spatial):
    w = model(spatial)
    ts = tracks()
    w.ingest_tracks(ts, 0)
    w.ingest_depth(track_depth(ts, depth(spatial))[0], 0)
    w.ingest_tracks(tracks(10, predicted=True), 10)
    history = w.snapshot(10).entities[0].history
    assert history[0].camera_point_meters == pytest.approx((0, 0, 5))
    assert history[0].depth_kind == "METRIC"
    assert history[1].camera_point_meters is None and history[1].depth_value is None


def test_world_model_implementation_is_replaceable(make_pipeline):
    class Alternate:
        def __init__(self, delegate):
            self.delegate = delegate
            self.closed = False

        def consume(self, result):
            return self.delegate.consume(result)

        def snapshot(self, timestamp):
            return self.delegate.snapshot(timestamp)

        def reset(self, session_id, source_id):
            self.delegate.reset(session_id, source_id)

        def close(self):
            self.closed = True
            self.delegate.close()

    p, recorder = make_pipeline({"world_model": {}, "record_session": True})
    replacement = Alternate(p.world_model)
    p.world_model = replacement
    p.run(SyntheticSource(iter([0, 10])))
    assert replacement.closed
    assert all(
        r["world_state"]["schema_version"] == 1
        for r in records(recorder)
        if r["type"] == "frame_result"
    )


def test_success_empty_is_distinct_from_absent_detector(geometry, config):
    from perception_lab.preprocessing import BasicPreprocessor

    w = model()
    f = next(iter(SyntheticSource(iter([300_000_000]))))
    batch = FixtureDetector().detect(
        BasicPreprocessor(geometry, config.preprocess).prepare(f), f.identity
    )
    w.ingest_detection("test", batch, 300_000_000)
    d = next(x for x in w.snapshot(300_000_000).subsystem_status if x.subsystem == "detector")
    assert d.observation_status == "SUCCESS_EMPTY" and d.status == S.FRESH
    assert not w.snapshot(300_000_001).entities


def test_wrong_session_depth_even_if_source_time_matches(spatial):
    w = model(spatial)
    w.ingest_tracks(tracks(), 0)
    d = track_depth(tracks(), depth(spatial))[0]
    with pytest.raises(ValueError):
        w.ingest_depth(replace(d, track_id=TrackId("other", 1)), 0)
    assert w.snapshot(0).entities[0].depth is None


def test_late_object_depth_does_not_overwrite_newer_source_failure(spatial):
    w = model(spatial)
    first = tracks()
    w.ingest_tracks(first, 0)
    w.ingest_tracks(tracks(10, offset=1), 10)
    w.failure("depth", "test", identity(20), 20)
    w.ingest_depth(track_depth(first, depth(spatial))[0], 20)
    s = w.snapshot(20)
    assert next(x for x in s.subsystem_status if x.subsystem == "depth").status == S.FAILED
    assert s.entities[0].depth_evidence.status == S.STALE


def test_supplied_ground_projection_and_bearing_are_guardian_candidates(spatial):
    w = model(spatial)
    w.ingest_tracks(tracks(), 0)
    _, sem = sample(spatial, "sidewalk")
    surface = SurfaceEvidenceExtractor().extract(sem)
    w.ingest_surface(surface, 0)
    w.ingest_pose(
        "test",
        SuppliedDepthPose(identity(), "device", "world", (0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)),
        P,
        0,
        "SYNTHETIC",
    )
    w.project_surface_pixel(
        "test",
        identity(),
        surface.regions[0].region_id,
        (4.0, 5.0),
        (0.0, 2.0, 0.0),
        (0.0, 1.0, 0.0),
        P,
        0,
    )
    s = w.snapshot(0)
    assert s.entities[0].bearing_radians == pytest.approx((0, 0))
    point = s.surface_state.projected_ground[0]
    assert point.position_meters == pytest.approx((1, 2, 8))
    assert point.source == "GROUND_PLANE_PROJECTED" and point.validation_status == "UNVERIFIED"
    assert point.identity == identity()


def test_ground_projection_rejects_missing_pose_or_mismatched_time(spatial):
    w = model(spatial)
    _, sem = sample(spatial, "sidewalk")
    surface = SurfaceEvidenceExtractor().extract(sem)
    w.ingest_surface(surface, 0)
    w.project_surface_pixel(
        "test",
        identity(),
        surface.regions[0].region_id,
        (4.0, 5.0),
        (0.0, 2.0, 0.0),
        (0.0, 1.0, 0.0),
        P,
        0,
    )
    assert not w.snapshot(0).surface_state.projected_ground
    w.ingest_pose(
        "test",
        SuppliedDepthPose(identity(1), "device", "world", (0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)),
        P,
        1,
    )
    w.project_surface_pixel(
        "test",
        identity(),
        surface.regions[0].region_id,
        (4.0, 5.0),
        (0.0, 2.0, 0.0),
        (0.0, 1.0, 0.0),
        P,
        1,
    )
    assert not w.snapshot(1).surface_state.projected_ground


@pytest.mark.parametrize("source", ["depth", "segmentation"])
def test_recoverable_component_failure_in_pipeline(make_pipeline, source):
    from perception_lab.contracts import FailureSeverity, LabError

    class Broken:
        provenance = ComponentProvenance("broken-fixture", source)

        def estimate_depth(self, image, identity):
            raise LabError("TEST_FAILURE", FailureSeverity.RECOVERABLE)

        def segment(self, image, identity):
            raise LabError("TEST_FAILURE", FailureSeverity.RECOVERABLE)

    p, r = make_pipeline({"world_model": {}, "record_session": True}, **{source: Broken()})
    p.run(SyntheticSource(iter([0])))
    state = next(row["world_state"] for row in records(r) if row["type"] == "frame_result")
    name = "semantics" if source == "segmentation" else source
    assert (
        next(x["status"] for x in state["subsystem_status"] if x["subsystem"] == name) == "FAILED"
    )
