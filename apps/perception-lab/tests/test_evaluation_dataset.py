import json

import pytest

from perception_lab.detector_runtime import file_hash
from perception_lab.evaluation_dataset import EvaluationDataset, audit_dataset, sample_indices


def manifest(tmp_path):
    image = tmp_path / "one.ppm"
    image.write_bytes(b"P6\n8 6\n255\n" + bytes(144))
    annotations = tmp_path / "annotations.json"
    annotations.write_text("{}")
    return {
        "schema_version": 1,
        "dataset": "TEST_FIXTURE_NOT_REAL_WORLD_EVIDENCE",
        "scope": "SENTINEL_REAL_WORLD",
        "annotation_sha256": file_hash(annotations),
        "sequences": [
            {
                "sequence_id": "one",
                "media_sha256": "1" * 64,
                "source_url_or_reference": "test fixture",
                "license_reference": "test fixture",
                "permission_status": "APPROVED_FOR_LOCAL_EVALUATION",
                "sampling_fps": 2.0,
                "sampling_policy": "PTS grid",
            }
        ],
        "images": [
            {
                "image_id": "one-0",
                "sequence_id": "one",
                "split": "TEST",
                "observation_ns": 0,
                "path": "one.ppm",
                "sha256": file_hash(image),
                "width": 8,
                "height": 6,
                "coordinate_space": "ORIGINAL_CAMERA_CONTINUOUS_EDGES",
                "annotations_reviewed": True,
                "metadata": dict.fromkeys(
                    ("lighting", "motion", "occlusion", "environment", "blur", "provenance"),
                    "UNKNOWN",
                ),
                "annotations": [{"label": "PERSON", "box": [1.0, 1.0, 3.0, 5.0]}],
            }
        ],
    }


def test_manifest_audit_counts_and_checks_image(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest(tmp_path)))
    result = audit_dataset(path, tmp_path / "annotations.json")
    assert result["objects"] == 1
    assert result["scenarios"]["motion"] == {"UNKNOWN": 1}
    (tmp_path / "one.ppm").write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        audit_dataset(path, tmp_path / "annotations.json")


def test_shelter_context_is_preserved_but_not_scored_as_p0(tmp_path):
    from perception_lab.detection import Box, Detection, ObjectClass
    from perception_lab.detector_benchmark import accuracy

    data = manifest(tmp_path)
    data["images"][0]["annotations"][0]["label"] = "SHELTER"
    with pytest.raises(ValueError, match="schema version 3"):
        EvaluationDataset.model_validate_json(json.dumps(data))
    data["schema_version"] = 3
    data["sequences"][0].update(parent_video_id="1" * 64, start_ns=0, end_ns=1)
    parsed = EvaluationDataset.model_validate_json(json.dumps(data)).model_dump(mode="json")
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(parsed))
    audited = audit_dataset(path, tmp_path / "annotations.json")
    assert audited["objects"] == 0
    assert audited["context_classes_excluded_from_p0"] == {"SHELTER": 1}
    prediction = Detection(6, "train", ObjectClass.TRAIN, 0.9, Box(1, 1, 3, 5))
    result = accuracy(parsed["images"], [(prediction,)], 0.25, 0.5)
    assert (result["tp"], result["fp"], result["fn"]) == (0, 1, 0)


@pytest.mark.parametrize(
    "box", [[1.0, 1.0, 1.0, 2.0], [-1.0, 1.0, 2.0, 3.0], [float("nan"), 1.0, 3.0, 4.0]]
)
def test_invalid_box_rejected(tmp_path, box):
    data = manifest(tmp_path)
    data["images"][0]["annotations"][0]["box"] = box
    with pytest.raises(ValueError):
        EvaluationDataset.model_validate_json(json.dumps(data))


def test_duplicate_and_split_leakage_rejected(tmp_path):
    data = manifest(tmp_path)
    data["images"].append({**data["images"][0]})
    with pytest.raises(ValueError, match="Duplicate frame"):
        EvaluationDataset.model_validate_json(json.dumps(data))
    data["images"][1].update(
        image_id="two", sha256="2" * 64, observation_ns=500, split="CALIBRATION"
    )
    with pytest.raises(ValueError, match="leakage"):
        EvaluationDataset.model_validate_json(json.dumps(data))


def test_duplicate_annotations_and_unreviewed_ground_truth_rejected(tmp_path):
    data = manifest(tmp_path)
    frame = data["images"][0]
    frame["annotations"] *= 2
    with pytest.raises(ValueError, match="Duplicate annotation"):
        EvaluationDataset.model_validate_json(json.dumps(data))
    frame["annotations"] = frame["annotations"][:1]
    frame["annotations_reviewed"] = False
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Unreviewed"):
        audit_dataset(path, tmp_path / "annotations.json")


def test_sampling_actual_pts_deterministic_no_duplicate_after_gap():
    assert sample_indices([100, 200, 500_000_100, 2_000_000_100, 2_000_000_200], 2) == (0, 2, 3)
    assert sample_indices([], 2) == ()
    with pytest.raises(ValueError):
        sample_indices([0, 0], 2)
    with pytest.raises(ValueError):
        sample_indices([0], float("nan"))
