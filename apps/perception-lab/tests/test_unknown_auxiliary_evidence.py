"""Unknown physical regions must participate in motion and surface evidence."""

from dataclasses import replace

import numpy as np
import pytest
from test_motion import camera as camera_fixture
from test_motion import scene
from test_semantics import sample
from test_track_semantics import evidence

from perception_lab.contracts import ComponentProvenance
from perception_lab.detection import Box
from perception_lab.entity_compatibility import legacy_batch
from perception_lab.motion_masking import dynamic_exclusions
from perception_lab.surfaces import SurfaceEvidenceExtractor, SurfaceFlag
from perception_lab.tracking import AssociationTracker
from perception_lab.tracking_config import TrackerConfig
from perception_lab.tracking_types import DetectorEvidence

camera = camera_fixture


@pytest.mark.parametrize("use_tracks", [False, True])
def test_unknown_region_excluded_from_static_motion_candidates(camera, use_tracks):
    flow, _ = scene(camera)
    observation = replace(evidence(1, None), source_frame=flow.pair.b, bbox=Box(0, 0, 320, 480))
    batch = legacy_batch(
        flow.pair.b, (observation,), ComponentProvenance("fixture", "detector"), "a" * 64
    )
    if use_tracks:
        tracker = AssociationTracker(
            TrackerConfig(), flow.pair.session_id, "clock", 640, 480, objectness_first=True
        )
        tracks = tracker.update(flow.pair.session_id, flow.pair.b, DetectorEvidence.SUCCESS, batch)
        actual = dynamic_exclusions(flow, tracks=tracks)
    else:
        actual = dynamic_exclusions(flow, detections=batch)
    assert np.array_equal(actual, flow.points_b[:, 0] < 320)
    assert actual.any() and not actual.all()


@pytest.mark.parametrize("use_tracks", [False, True])
def test_unknown_occupancy_does_not_relabel_sidewalk(geometry, use_tracks):
    _, semantic = sample(geometry, "sidewalk")
    observation = replace(evidence(0, None), source_frame=semantic.identity, bbox=Box(1, 1, 3, 3))
    batch = legacy_batch(
        semantic.identity, (observation,), ComponentProvenance("fixture", "detector"), "a" * 64
    )
    kwargs = {"detections": batch}
    if use_tracks:
        tracker = AssociationTracker(
            TrackerConfig(), semantic.session_id, "synthetic", 8, 6, objectness_first=True
        )
        kwargs = {
            "tracks": tracker.update(
                semantic.session_id, semantic.identity, DetectorEvidence.SUCCESS, batch
            )
        }
    surface = SurfaceEvidenceExtractor().extract(semantic, **kwargs)
    occupied = surface.evidence & int(SurfaceFlag.OCCUPIED_REGION)
    assert np.count_nonzero(occupied) == 4
    assert occupied[1:3, 1:3].all()
    assert np.unique(semantic.labels).size == 1
