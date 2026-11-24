"""Orientation reaches model inputs while detections retain original camera geometry."""

from dataclasses import replace
from math import radians

import numpy as np
import pytest
from conftest import records
from test_camera_orientation import image

from perception_lab.camera_orientation import CameraOrientationState
from perception_lab.components import NoOpDetector
from perception_lab.config import LabConfig
from perception_lab.orientation_preprocessing import build_preprocessor
from perception_lab.sources import SyntheticSource


def metadata(frame, *, cardinal=90, roll=None):
    return CameraOrientationState(
        frame.identity,
        cardinal,
        "GOOD",
        "SYNTHETIC_TEST",
        "orientation-fixture",
        roll_radians=None if roll is None else radians(roll),
    )


def test_cardinal_preprocessing_is_opt_in_and_inverse_maps(config, geometry):
    frame = image(geometry)
    frame = replace(frame, camera_orientation=metadata(frame))
    raw = build_preprocessor(geometry, config).prepare(frame)
    np.testing.assert_array_equal(raw.pixels, frame.pixels)
    active = build_preprocessor(
        geometry, config.model_copy(update={"orientation_canonicalization": True})
    )
    prepared = active.prepare(frame)
    np.testing.assert_array_equal(prepared.pixels, np.rot90(frame.pixels, -1))
    assert prepared.mapping.inverse(*prepared.mapping.forward(2.5, 1.5)) == pytest.approx(
        (2.5, 1.5)
    )


def test_total_roll_is_not_added_to_cardinal_rotation(config, geometry):
    frame = image(geometry)
    active = build_preprocessor(
        geometry, config.model_copy(update={"orientation_canonicalization": True})
    )
    first = active.prepare(replace(frame, camera_orientation=metadata(frame, cardinal=90, roll=30)))
    second = active.prepare(replace(frame, camera_orientation=metadata(frame, cardinal=0, roll=30)))
    np.testing.assert_array_equal(first.pixels, second.pixels)
    assert first.mapping.forward(2.5, 1.5) == pytest.approx(second.mapping.forward(2.5, 1.5))


def test_unavailable_orientation_and_pitch_yaw_do_not_invent_roll(config, geometry):
    frame = image(geometry)
    active = build_preprocessor(
        geometry, config.model_copy(update={"orientation_canonicalization": True})
    )
    for orientation in [
        None,
        replace(metadata(frame), quality="UNKNOWN"),
        replace(metadata(frame, cardinal=None), pitch_radians=0.5, yaw_radians=1.0),
    ]:
        result = active.prepare(replace(frame, camera_orientation=orientation))
        np.testing.assert_array_equal(result.pixels, frame.pixels)


def test_orientation_rejects_cross_frame_metadata_and_unsupported_preprocess(config, geometry):
    frame = image(geometry)
    with pytest.raises(ValueError, match="another source frame"):
        replace(
            frame,
            camera_orientation=replace(
                metadata(frame), identity=replace(frame.identity, sequence=99)
            ),
        )
    with pytest.raises(ValueError, match="identity NHWC"):
        LabConfig.model_validate(
            {
                **config.model_dump(),
                "orientation_canonicalization": True,
                "preprocess": {"operation": "resize", "width": 4, "height": 4},
            }
        )


def test_pipeline_delivers_canonical_input_and_preserves_source_orientation(
    make_pipeline, geometry
):
    seen = []

    class Detector(NoOpDetector):
        def detect(self, prepared, identity):
            seen.append((identity, prepared.descriptor.width, prepared.descriptor.height))
            return super().detect(prepared, identity)

    pipeline, recorder = make_pipeline(
        {"record_session": True, "orientation_canonicalization": True}, detector=Detector()
    )
    pipeline.preprocessor = build_preprocessor(geometry, pipeline.config)

    class OrientedSource(SyntheticSource):
        def __iter__(self):
            for frame in super().__iter__():
                yield replace(frame, camera_orientation=metadata(frame))

    pipeline.run(OrientedSource(iter([0, 100_000_000])))
    assert [(w, h) for _, w, h in seen] == [(6, 8), (6, 8)]
    frames = [r for r in records(recorder) if r["type"] == "frame_result"]
    assert len(frames) == 2
    for row in frames:
        assert not row["errors"]
        assert row["camera_orientation"]["identity"] == row["identity"]
        assert row["camera_orientation"]["sensor_rotation_degrees"] == 90
        assert (row["width"], row["height"]) == (8, 6)
