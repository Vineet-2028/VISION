from types import SimpleNamespace

import numpy as np
import pytest

from perception_lab.config import PreprocessConfig
from perception_lab.contracts import ComponentProvenance
from perception_lab.edge_runtime import PicoDetDetector, YoloXDetector, yolox_rows
from perception_lab.preprocessing import BasicPreprocessor
from perception_lab.sources import SyntheticSource


@pytest.mark.parametrize("adapter", [YoloXDetector, PicoDetDetector])
def test_adapter_restores_analytical_boxes_and_preserves_identity(geometry, adapter):
    frame = next(iter(SyntheticSource(iter([123_456_789]))))
    prepared = BasicPreprocessor(geometry, PreprocessConfig()).prepare(frame)
    detector = adapter.__new__(adapter)
    detector.confidence = 0.25
    detector.provenance = ComponentProvenance("fixture", "detector", "fixture", "1" * 64)
    detector.cv = SimpleNamespace(
        INTER_LINEAR=1,
        resize=lambda pixels, size, interpolation: np.broadcast_to(
            np.array([10, 20, 30], dtype=np.uint8), (size[1], size[0], 3)
        ).copy(),
    )

    def infer(names, inputs):
        tensor = inputs["image"]
        assert tensor.shape == (1, 3, 416, 416)
        if adapter == YoloXDetector:
            assert tensor[0, :, 0, 0] == pytest.approx([30, 20, 10])
            raw = np.zeros((1, 3549, 85), dtype=np.float32)
            raw[0, 0, :4] = [26, 19.5, np.log(26), np.log(26)]
            raw[0, 0, 4:6] = [0.9, 1.0]
            return [raw]
        assert inputs["scale_factor"].tolist() == [[1.0, 1.0]]
        return [np.array([[0, 0.9, 104, 416 / 6, 312, 416 * 5 / 6]], dtype=np.float32)]

    detector.session = SimpleNamespace(
        get_inputs=lambda: [SimpleNamespace(name="image")], run=infer
    )
    batch = detector.detect(prepared, frame.identity)
    assert batch.identity == frame.identity
    assert batch.provenance == detector.provenance
    assert len(batch.detections) == 1
    assert batch.detections[0].box.coordinates == pytest.approx((2, 1, 6, 5), abs=1e-5)
    core = geometry.detection_to_core(batch.detections[0], batch.identity)
    assert geometry.model.groundContactRayCandidate(core).isPresent()
    assert batch.transform_hash != prepared.mapping.fingerprint


def test_yolox_invalid_output_never_empty_success():
    with pytest.raises(ValueError, match="Invalid"):
        yolox_rows(np.full((1, 3549, 85), np.nan, dtype=np.float32), 0.25)


def test_guard_band_windows_and_schema_reject_overlap(tmp_path):
    from test_first_person import paired
    from test_qualification_tools import tool

    from perception_lab.evaluation_dataset import EvaluationDataset

    assert tool("prepare_first_person").windows(0, 1_500_000_000_000) == [
        ("TRAIN_DEV", 0, 552_000_000_000),
        ("CALIBRATION", 612_000_000_000, 957_000_000_000),
        ("TEST", 1_017_000_000_000, 1_500_000_000_000),
    ]
    data, _, _ = paired(tmp_path)
    data["schema_version"] = 2
    for i, sequence in enumerate(data["sequences"]):
        sequence.update(
            media_sha256="1" * 64,
            parent_video_id="1" * 64,
            start_ns=i * 70_000_000_000,
            end_ns=(i * 70 + 10) * 1_000_000_000,
        )
        data["images"][i]["observation_ns"] = sequence["start_ns"]
    import json

    EvaluationDataset.model_validate_json(json.dumps(data))
    data["sequences"][1]["start_ns"] -= 1
    with pytest.raises(ValueError, match="guard"):
        EvaluationDataset.model_validate_json(json.dumps(data))
