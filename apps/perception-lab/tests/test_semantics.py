import gc
import weakref
from concurrent.futures import Future
from dataclasses import replace
from threading import Event

import numpy as np
import pytest
from conftest import records

from perception_lab.config import PreprocessConfig
from perception_lab.contracts import ComponentProvenance, FrameIdentity, TimingProvenance
from perception_lab.depth import (
    DepthAxis,
    DepthDirection,
    DepthFrame,
    DepthKind,
    DepthRepresentation,
)
from perception_lab.detection import Box, Detection, DetectionBatch, ObjectClass
from perception_lab.preprocessing import BasicPreprocessor
from perception_lab.scheduling import QueuedFrame
from perception_lab.semantic_evaluation import decode_runs, evaluate_masks
from perception_lab.semantic_runtime import SyntheticSegmenter, map_cityscapes
from perception_lab.semantic_worker import SemanticWorker
from perception_lab.semantics import ObservationStatus, restore_labels
from perception_lab.semantics import SemanticClass as C
from perception_lab.sources import SyntheticSource
from perception_lab.surfaces import SurfaceEvidenceExtractor, SurfacePolicy, depth_consistency
from perception_lab.surfaces import SurfaceFlag as F
from perception_lab.tracking_types import DetectorEvidence, TrackSet


def sample(geometry, pattern="split", preprocess=None):
    frame = next(iter(SyntheticSource(iter([0]))))
    image = BasicPreprocessor(geometry, preprocess or PreprocessConfig()).prepare(frame)
    return image, SyntheticSegmenter("test", pattern).segment(image, frame.identity)


@pytest.mark.parametrize("pattern", ["sidewalk", "split", "path", "stairs", "unknown", "dynamic"])
def test_synthetic_patterns_preserve_contract(geometry, pattern):
    _, s = sample(geometry, pattern)
    result = SurfaceEvidenceExtractor().extract(s)
    assert result.identity == s.identity
    assert result.evidence.shape == (6, 8)
    assert s.status == ObservationStatus.OBSERVED
    assert s.age_ns == 0
    assert s.labels.dtype == np.uint8
    with pytest.raises(ValueError):
        s.labels.setflags(write=True)


def test_surface_policy_road_stairs_unknown_are_not_potential(geometry):
    _, s = sample(geometry)
    labels = np.array(
        [[C.SIDEWALK, C.ROAD, C.STAIRS, C.UNKNOWN, C.GRASS, C.CURB, C.FLOOR, C.PATH]] * 6, np.uint8
    )
    result = SurfaceEvidenceExtractor().extract(replace(s, labels=labels))
    assert list(np.flatnonzero(result.evidence[0] & int(F.POTENTIAL_TRAVERSABLE))) == [0, 6, 7]
    assert result.evidence[0, 1] & int(F.GROUND_CANDIDATE)
    assert not result.evidence[0, 1] & int(F.OBSTACLE_EVIDENCE)
    assert result.evidence[0, 3] & int(F.UNKNOWN)


@pytest.mark.parametrize(
    "operation,width,height", [("resize", 4, 3), ("letterbox", 8, 8), ("crop", 4, 3)]
)
def test_original_coordinates_and_nearest_labels(geometry, operation, width, height):
    _, s = sample(
        geometry, "sidewalk", PreprocessConfig(operation=operation, width=width, height=height)
    )
    restored = restore_labels(s)
    assert restored.shape == (6, 8)
    assert set(np.unique(restored)) <= {0, 1}
    if operation == "crop":
        assert np.all(restored[:3, :4] == C.SIDEWALK)
        assert np.all(restored[3:] == C.UNKNOWN)
    else:
        assert np.all(restored == C.SIDEWALK)


def test_bottom_connectivity_does_not_delete_island_or_unknown(geometry):
    _, s = sample(geometry)
    labels = np.zeros((6, 8), np.uint8)
    labels[:2, :2] = C.SIDEWALK
    labels[4:, 4:6] = C.SIDEWALK
    result = SurfaceEvidenceExtractor().extract(replace(s, labels=labels))
    regions = [r for r in result.regions if r.label == C.SIDEWALK]
    assert sorted(r.connected_to_bottom for r in regions) == [False, True]
    assert sum(r.pixel_area for r in regions) == 8
    assert np.count_nonzero(result.evidence & int(F.UNKNOWN)) == 40


def test_model_mapping_terrain_is_broad_and_stairs_unsupported():
    mapped = map_cityscapes(np.arange(19, dtype=np.int64)[None])
    assert mapped[0, 9] == C.GROUND_OTHER
    assert C.STAIRS not in mapped
    assert C.CURB not in mapped
    with pytest.raises(ValueError):
        map_cityscapes(np.array([[255]], np.int64))


def test_wrong_taxonomy_labels_and_observation_rejected(geometry):
    _, s = sample(geometry)
    for change in [
        {"taxonomy": "future"},
        {"labels": np.full((6, 8), 255, np.uint8)},
        {"observed_identity": replace(s.identity, sequence=1)},
        {"identity": replace(s.identity, observation_ns=1)},
        {"supported_classes": frozenset({C.ROAD})},
    ]:
        with pytest.raises(ValueError):
            replace(s, **change)


@pytest.mark.parametrize("provider", ["PicoDet-S", "YOLOX-Nano"])
def test_detector_swap_occupancy_preserves_semantics(geometry, provider):
    _, s = sample(geometry, "sidewalk")
    batch = DetectionBatch(
        s.identity,
        (Detection(2, "car", ObjectClass.CAR, 0.9, Box(1, 1, 3, 3)),),
        ComponentProvenance(provider, "detector"),
        "a" * 64,
        0,
        0,
    )
    surface = SurfaceEvidenceExtractor().extract(s, batch)
    assert np.count_nonzero(surface.evidence & int(F.OCCUPIED_REGION)) == 4
    assert np.all(s.labels == C.SIDEWALK)
    assert surface.detection_provenance.name == provider
    with pytest.raises(ValueError, match="mismatch"):
        SurfaceEvidenceExtractor().extract(
            s, replace(batch, identity=replace(s.identity, sequence=1))
        )


def test_oversized_overlay_diagnostic_and_tracker_session(geometry):
    _, s = sample(geometry)
    batch = DetectionBatch(
        s.identity,
        (Detection(2, "car", ObjectClass.CAR, 0.9, Box(0, 0, 8, 6)),),
        ComponentProvenance("d", "detector"),
        "a" * 64,
        0,
        0,
    )
    surface = SurfaceEvidenceExtractor().extract(s, batch)
    assert "OVERSIZED_OVERLAY_IGNORED" in surface.diagnostics
    track = TrackSet(
        "test",
        s.identity,
        (),
        (),
        DetectorEvidence.UNAVAILABLE,
        (),
        ComponentProvenance("alternate", "tracker"),
    )
    assert SurfaceEvidenceExtractor().extract(s, tracks=track).track_provenance.name == "alternate"
    with pytest.raises(ValueError):
        SurfaceEvidenceExtractor().extract(s, tracks=replace(track, session_id="other"))


@pytest.mark.parametrize("provider", ["depth-a", "depth-b"])
def test_depth_swap_discontinuity_is_qualitative(geometry, provider):
    _, s = sample(geometry, "sidewalk")
    values = np.ones((6, 8), np.float32)
    values[:, 4:] = 3
    depth = DepthFrame(
        s.identity,
        DepthRepresentation(DepthKind.METRIC, DepthDirection.LARGER_IS_FARTHER, DepthAxis.CAMERA_Z),
        values,
        np.ones((6, 8), np.bool_),
        s.mapping,
        ComponentProvenance(provider, "depth"),
        0,
        1,
    )
    result = depth_consistency(s, depth)
    assert result["status"] == "QUALITATIVE_ONLY"
    assert result["relative_jump_p95"] > 0
    assert result["depth_provenance"]["name"] == provider
    with pytest.raises(ValueError):
        depth_consistency(s, replace(depth, identity=replace(s.identity, sequence=1)))


def test_partial_labels_false_traversable_and_boundary_metrics():
    truth = np.full((10, 10), C.WALL, np.uint8)
    truth[5:] = C.SIDEWALK
    truth[:, 0] = 255
    predicted = truth.copy()
    predicted[:, 0] = C.ROAD
    predicted[0, 1] = C.SIDEWALK
    result = evaluate_masks(predicted, truth, review_status="HUMAN_REVIEWED")
    assert result["reviewed_pixels"] == 90
    assert result["obstacle_as_traversable_pixels"] == 1
    assert result["false_traversable_pixels"] == 1
    assert result["classes"]["SIDEWALK"]["recall"] == 1
    assert result["boundary_f1_1px"] < 1
    with pytest.raises(ValueError, match="reviewed"):
        evaluate_masks(predicted, truth, review_status="DRAFT_MODEL_ASSISTED")
    with pytest.raises(ValueError, match="No reviewed"):
        evaluate_masks(predicted, np.full((10, 10), 255, np.uint8), review_status="HUMAN_REVIEWED")


@pytest.mark.parametrize("runs", [[[1, 49]], [[255, -1]], [[20, 48]], [[1, 47]], [[True, 48]]])
def test_annotation_rle_rejects_invalid(runs):
    with pytest.raises(ValueError):
        decode_runs(runs, 8, 6)


def test_semantic_cadence_recording_and_no_other_components(make_pipeline):
    pipeline, recorder = make_pipeline(
        {"record_session": True, "intervals_ns": {"segmentation": 30}}
    )
    pipeline.segmentation = SyntheticSegmenter(recorder.session_id)
    pipeline.run(SyntheticSource(iter([0, 10, 20, 30])))
    rows = [r for r in records(recorder) if r["type"] == "frame_result"]
    assert [r["segmentation"] is not None for r in rows] == [True, False, False, True]
    assert all(r["depth"] is None and r["detector"] is None for r in rows)
    assert recorder.manifest["schema_version"] == 5
    assert "labels" not in rows[0]["segmentation"]
    assert "evidence" not in rows[0]["surfaces"]


def test_single_worker_skips_busy_jobs_and_releases(geometry):
    image, s = sample(geometry)
    entered, release = Event(), Event()

    class Slow:
        provenance = s.provenance

        def segment(self, image, identity):
            entered.set()
            assert release.wait(10)
            return s

    worker = SemanticWorker(Slow())
    try:
        worker.submit(image, s.identity)
        assert entered.wait(10)
        for _ in range(100):
            worker.submit(image, s.identity)
        assert worker.poll() is None
        assert worker.submitted == 1 and worker.skipped == 100
        release.set()
        assert worker.pending.result(timeout=10) is s
        assert worker.poll() is s
        assert worker.pending is None
    finally:
        release.set()
        worker.close()


def test_many_semantic_frames_release_buffers(geometry):
    image, s = sample(geometry)
    provider = SyntheticSegmenter("test")
    refs = []
    for i in range(2000):
        semantic = provider.segment(
            image, FrameIdentity("synthetic", i, i, TimingProvenance.SYNTHETIC)
        )
        refs.append(weakref.ref(semantic.labels))
    del semantic
    gc.collect()
    assert all(ref() is None for ref in refs)
    assert not hasattr(provider, "history")


def test_stale_surface_has_no_current_ground_claim(geometry):
    _, s = sample(geometry, "sidewalk")
    result = SurfaceEvidenceExtractor(SurfacePolicy(maximum_regions=1)).extract(
        replace(s, status=ObservationStatus.STALE)
    )
    assert np.all(result.evidence == int(F.UNKNOWN))
    assert result.regions == ()


def test_async_publication_retains_old_identity_and_expires(make_pipeline, geometry):
    pipeline, recorder = make_pipeline({"record_session": True})
    image, semantic = sample(geometry, "sidewalk")
    semantic = replace(semantic, session_id=recorder.session_id)
    worker = SemanticWorker(SyntheticSegmenter(recorder.session_id))
    worker.pending = Future()
    worker.pending.set_result(semantic)
    pipeline.semantic_worker = worker
    current = next(iter(SyntheticSource(iter([2_000_000_000]))))
    current = replace(current, identity=replace(current.identity, sequence=1))
    try:
        pipeline.process(QueuedFrame(current, pipeline.clock(), pipeline.clock()))
        recorder.close()
        row = [r for r in records(recorder) if r["type"] == "frame_result"][0]
        assert row["identity"]["observation_ns"] == 2_000_000_000
        assert row["segmentation"]["identity"]["observation_ns"] == 0
        assert row["segmentation"]["status"] == "STALE"
        assert row["surfaces"]["flag_pixels"]["POTENTIAL_TRAVERSABLE"] == 0
        assert row["surfaces"]["flag_pixels"]["UNKNOWN"] == 48
    finally:
        worker.close()
        recorder.close()


def test_missing_boundary_scores_zero():
    truth = np.full((10, 10), C.SIDEWALK, np.uint8)
    truth[:5] = C.ROAD
    predicted = np.full((10, 10), C.SIDEWALK, np.uint8)
    result = evaluate_masks(predicted, truth, review_status="HUMAN_REVIEWED")
    assert result["boundary_f1_1px"] == 0.0


def test_semantic_outputs_reject_wrong_camera_image(make_pipeline, geometry, calibration):
    from perception_lab.contracts import LabError
    from perception_lab.geometry import CoreGeometry

    pipeline, recorder = make_pipeline()
    raw = calibration.model_dump()
    raw["image_frame_id"] = "other-camera-image"
    other = CoreGeometry(type(calibration).model_validate(raw))
    _, semantic = sample(other)
    semantic = replace(semantic, session_id=recorder.session_id)

    class WrongCamera:
        provenance = semantic.provenance

        def segment(self, image, identity):
            return semantic

    pipeline.segmentation = WrongCamera()
    with pytest.raises(LabError):
        pipeline.run(SyntheticSource(iter([0])))
