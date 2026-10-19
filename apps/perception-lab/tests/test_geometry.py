import numpy as np
import pytest

from perception_lab.config import Calibration, PreprocessConfig
from perception_lab.contracts import LabError
from perception_lab.geometry import CoreGeometry
from perception_lab.preprocessing import BasicPreprocessor
from perception_lab.sources import SyntheticSource


@pytest.mark.parametrize(
    "operation,width,height,left,top",
    [
        ("identity", None, None, 0, 0),
        ("resize", 16, 12, 0, 0),
        ("crop", 4, 3, 2, 1),
        ("letterbox", 11, 11, 0, 0),
    ],
)
def test_preprocess_preserves_core_inverse(geometry, operation, width, height, left, top):
    frame = next(iter(SyntheticSource(iter([0]))))
    pre = BasicPreprocessor(
        geometry,
        PreprocessConfig(operation=operation, width=width, height=height, left=left, top=top),
    )
    output = pre.prepare(frame)
    assert output.pixels.shape == (height or 6, width or 8, 3)
    for point in ((0.0, 0.0), (4.0, 3.0), (8.0, 6.0), (1.5, 2.5)):
        assert output.mapping.inverse(*output.mapping.forward(*point)) == pytest.approx(point)
    if operation == "identity":
        assert output.pixels is frame.pixels
    if operation == "crop":
        assert output.mapping.forward(2.0, 1.0) == (0.0, 0.0)
        assert np.shares_memory(output.pixels, frame.pixels)
    if operation == "letterbox":
        assert output.mapping.forward(0.0, 0.0) == (0.0, 1.0)
        assert output.mapping.forward(8.0, 6.0) == (11.0, 9.0)


@pytest.mark.parametrize(
    "pixel_format,channels", [("RGB", 3), ("BGR", 3), ("GRAY", 1), ("RGBA", 4)]
)
def test_explicit_format_and_layout(geometry, pixel_format, channels):
    output = BasicPreprocessor(
        geometry, PreprocessConfig(pixel_format=pixel_format, layout="NCHW")
    ).prepare(next(iter(SyntheticSource(iter([0])))))
    assert output.pixels.shape == (channels, 6, 8)
    assert output.descriptor.layout == "NCHW"
    assert not output.pixels.flags.writeable


def test_wrong_resolution_never_reuses_calibration(geometry):
    with pytest.raises(LabError, match="RESOLUTION"):
        BasicPreprocessor(geometry, PreprocessConfig()).prepare(
            next(iter(SyntheticSource(iter([0]), width=9)))
        )


def test_core_inspection_center_and_direction(geometry):
    center = geometry.inspect(4.0, 3.0)
    assert center["camera_ray"] == [0.0, 0.0, 1.0]
    assert center["normalized_camera"] == [0.0, 0.0]
    assert geometry.inspect(5.0, 2.0)["horizontal_bearing_radians"] > 0
    assert geometry.inspect(5.0, 2.0)["vertical_bearing_radians"] > 0


def test_distortion_domain_validated_by_java(calibration):
    raw = calibration.model_dump()
    raw.update(
        distortion_model="brown_conrady",
        distortion_coefficients={
            "k1": -2.0,
            "k2": 0.0,
            "k3": 0.0,
            "p1": 0.0,
            "p2": 0.0,
            "max_radius": 2.0,
        },
    )
    with pytest.raises(Exception, match="domain|invert|ambiguous|Jacobian|Distortion"):
        CoreGeometry(Calibration.model_validate(raw))


def test_extrinsics_not_defaulted_and_bad_quaternion_rejected(calibration, geometry):
    assert geometry.extrinsics is None
    raw = calibration.model_dump()
    raw["camera_to_device"] = {
        "version": "test",
        "device_frame_id": "body",
        "rotation_wxyz": [0.0, 0.0, 0.0, 0.0],
        "translation_meters": [0.0, 0.0, 0.0],
    }
    with pytest.raises(Exception, match="quaternion|Quaternion|norm|Norm"):
        CoreGeometry(Calibration.model_validate(raw))
