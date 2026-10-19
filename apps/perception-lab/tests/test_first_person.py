import copy
import json

import pytest
from test_evaluation_dataset import manifest
from test_qualification_tools import tool

from perception_lab.first_person import allocate, discover, event_sample_indices


def test_annotation_json_can_exceed_config_limit_without_relaxing_config(tmp_path):
    from perception_lab.config import read_json

    path = tmp_path / "large.json"
    path.write_text(json.dumps({"annotations": "x" * 1_000_001}))
    with pytest.raises(ValueError, match="size limit"):
        read_json(path)
    assert len(read_json(path, max_bytes=64_000_000)["annotations"]) == 1_000_001
    path.write_text('{"a": 1, "a": 2}')
    with pytest.raises(ValueError, match="Duplicate"):
        read_json(path, max_bytes=64_000_000)


@pytest.mark.parametrize("mutation", ["unreviewed", "timestamp", "dataset"])
def test_review_import_rejects_incomplete_or_changed_identity(tmp_path, mutation):
    data = manifest(tmp_path)
    (tmp_path / "manifest.draft.json").write_text(json.dumps(data))
    if mutation == "unreviewed":
        data["images"][0]["annotations_reviewed"] = False
    elif mutation == "timestamp":
        data["images"][0]["observation_ns"] = 1
    else:
        data["dataset"] = "CHANGED"
    review = tmp_path / "review.json"
    review.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="review|identity"):
        tool("review_first_person").finalize(tmp_path, review)
    assert not (tmp_path / "manifest.reviewed.json").exists()


def test_review_import_hashes_review_and_never_overwrites(tmp_path):
    from perception_lab.detector_runtime import file_hash

    data = manifest(tmp_path)
    (tmp_path / "manifest.draft.json").write_text(json.dumps(data))
    review = tmp_path / "review.json"
    review.write_text(json.dumps(data))
    workflow = tool("review_first_person")
    workflow.finalize(tmp_path, review)
    saved = json.loads((tmp_path / "manifest.reviewed.json").read_text())
    assert saved["annotation_sha256"] == file_hash(review)
    with pytest.raises(FileExistsError):
        workflow.finalize(tmp_path, review)


def test_discovery_empty_and_nested_case_insensitive(tmp_path):
    assert discover(tmp_path) == ()
    child = tmp_path / "nested"
    child.mkdir()
    video = child / "clip.MP4"
    video.write_bytes(b"test only")
    (child / "unrelated.txt").write_text("not video")
    assert discover(tmp_path) == (video,)


def test_whole_sequence_allocation_order_independent_duplicates_rejected(tmp_path):
    videos = tuple(tmp_path / f"{i}.mp4" for i in range(4))
    for i, video in enumerate(videos):
        video.write_bytes(bytes([i]))
    result = allocate(videos)
    assert result == allocate(tuple(reversed(videos)))
    assert [split for _, split in result.values()].count("CALIBRATION") == 2
    assert [split for _, split in result.values()].count("TEST") == 2
    videos[1].write_bytes(videos[0].read_bytes())
    with pytest.raises(ValueError, match="Duplicate"):
        allocate(videos)


def test_event_sampling_preserves_base_without_duplicates():
    times = list(range(0, 2_000_000_000, 100_000_000))
    assert event_sample_indices(times) == (0, 5, 10, 15)
    assert event_sample_indices(times, ((500_000_000, 1_100_000_000),)) == (0, 5, 7, 9, 10, 15)
    with pytest.raises(ValueError):
        event_sample_indices(times, ((10, 9),))


def paired(tmp_path):
    data = manifest(tmp_path)
    first = data["images"][0]
    first["split"] = "CALIBRATION"
    second = copy.deepcopy(first)
    second.update(image_id="two-0", sequence_id="two", split="TEST", sha256="2" * 64)
    data["images"].append(second)
    data["sequences"].append(
        {**data["sequences"][0], "sequence_id": "two", "media_sha256": "2" * 64}
    )
    prediction = {
        "class_id": 0,
        "class_name": "person",
        "label": "PERSON",
        "confidence": 0.8,
        "box": {"x1": 1.0, "y1": 1.0, "x2": 3.0, "y2": 5.0},
    }
    report = {
        "status": "MEASURED_LOCALLY",
        "candidate": {"model_version": "1" * 64},
        "configuration": {"confidence_floor": 0.01},
        "dataset_sha256": "3" * 64,
        "evaluation_split": "CALIBRATION",
        "image_ids": ["one-0"],
        "predictions": [{"image_id": "one-0", "detections": [prediction]}],
    }
    qualification = {
        **report,
        "evaluation_split": "TEST",
        "image_ids": ["two-0"],
        "predictions": [{"image_id": "two-0", "detections": []}],
    }
    return data, report, qualification


def test_real_world_analysis_rejects_drafts_and_unknown_schema(tmp_path):
    data, report, _ = paired(tmp_path)
    workflow = tool("qualify_detectors")
    report["schema_version"] = 999
    with pytest.raises(ValueError, match="schema"):
        workflow.analyze(report, data)
    report["schema_version"] = 1
    data["images"][0]["annotations_reviewed"] = False
    with pytest.raises(ValueError, match="human-reviewed"):
        workflow.analyze(report, data)


def test_real_world_cli_cannot_use_posthoc_sweep(tmp_path, monkeypatch):
    data, _, _ = paired(tmp_path)
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(data))
    monkeypatch.setattr(
        "sys.argv",
        [
            "qualify_detectors",
            "--dataset",
            str(path),
            "--runs",
            str(tmp_path / "unused.json"),
            "--output",
            str(tmp_path / "result"),
        ],
    )
    with pytest.raises(SystemExit) as error:
        tool("qualify_detectors").main()
    assert error.value.code == 2
    assert not (tmp_path / "result.json").exists()


def test_frozen_threshold_cannot_retune_to_qualification(tmp_path):
    data, calibration, qualification = paired(tmp_path)
    workflow = tool("qualify_detectors")
    frozen = workflow.freeze(calibration, data)
    original = copy.deepcopy(frozen)
    result = workflow.qualify_frozen(frozen, qualification, data)
    entry = result["operating_points"]["fp100"][0]
    assert entry["calibration"]["recall"] == 1
    assert entry["qualification"]["recall"] == 0
    assert entry["qualification"]["threshold"] == entry["calibration"]["threshold"]
    assert frozen == original
    with pytest.raises(ValueError, match="CALIBRATION"):
        workflow.freeze(qualification, data)


@pytest.mark.parametrize("key", ["candidate", "configuration", "dataset_sha256"])
def test_frozen_provenance_mismatch_rejected(tmp_path, key):
    data, calibration, qualification = paired(tmp_path)
    workflow = tool("qualify_detectors")
    frozen = workflow.freeze(calibration, data)
    qualification[key] = "changed"
    with pytest.raises(ValueError, match="mismatch"):
        workflow.qualify_frozen(frozen, qualification, data)
