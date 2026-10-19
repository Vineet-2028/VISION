import hashlib
import json

import pytest

from perception_lab.detection import Box, ObjectClass
from perception_lab.tracking_dataset import TrackingDataset, validate_review
from perception_lab.tracking_evaluation import LabeledBox, evaluate_sequence


def box(identity="g", x=0):
    return LabeledBox(identity, ObjectClass.PERSON, Box(x, 0, x + 10, 10))


def test_identity_counts_switch_fragmentation_hand_computable():
    result = evaluate_sequence([((box(),), (box("p"),)), ((box(),), ()), ((box(),), (box("q"),))])
    assert (result["tp"], result["fn"], result["fp"]) == (2, 1, 0)
    assert result["id_switches"] == 1 and result["fragmentations"] == 1
    assert result["identity_tp"] == 1
    assert result["identity_precision"] == 0.5
    assert result["identity_recall"] == pytest.approx(1 / 3)
    assert result["identity_f1"] == 0.4


def test_duplicate_and_empty_metrics():
    d = evaluate_sequence([((box(),), (box("p"), box("q")))])
    assert d["duplicate_observations"] == 1 and d["fp"] == 1
    assert d["identity_f1"] == pytest.approx(2 / 3)
    assert evaluate_sequence([])["identity_f1"] is None
    with pytest.raises(ValueError):
        evaluate_sequence([((box(), box()), ())])


def test_matching_prioritizes_valid_match_count_before_overlap():
    # Perfect g1/p1 must not steal p1 from g2 when g1 can use p2.
    result = evaluate_sequence([((box("g1", 0), box("g2", -3)), (box("p1", 0), box("p2", 3)))])
    assert (result["tp"], result["fp"], result["fn"]) == (2, 0, 0)


def packet(tmp_path):
    image = tmp_path / "fixture.jpg"
    image.write_bytes(b"synthetic hash fixture, not decoded")
    return {
        "schema_version": 1,
        "dataset": "fixture",
        "source_sha256": "a" * 64,
        "frames": [
            {
                "image_id": "frame",
                "clip_id": "clip",
                "observation_ns": 0,
                "path": "fixture.jpg",
                "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                "width": 100,
                "height": 100,
                "annotations": [
                    {"ground_truth_track_id": "1", "label": "PERSON", "box": [0.0, 0.0, 10.0, 10.0]}
                ],
            }
        ],
    }


def test_draft_ids_cannot_be_evaluated_and_frozen_identity_cannot_change(tmp_path):
    data = packet(tmp_path)
    draft = tmp_path / "draft.json"
    review = tmp_path / "review.json"
    draft.write_text(json.dumps(data))
    review.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="HUMAN_TRACK"):
        validate_review(draft, review)
    data["frames"][0]["review_status"] = "REVIEWED_TRACK_ID"
    review.write_text(json.dumps(data))
    assert len(validate_review(draft, review).frames) == 1
    data["frames"][0]["observation_ns"] = 1
    review.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="identity"):
        validate_review(draft, review)


def test_duplicate_ids_and_invalid_boxes_rejected(tmp_path):
    data = packet(tmp_path)
    data["frames"][0]["annotations"] *= 2
    with pytest.raises(ValueError, match="duplicated"):
        TrackingDataset.model_validate_json(json.dumps(data))


def test_review_path_escape_rejected(tmp_path):
    data = packet(tmp_path)
    data["frames"][0]["path"] = "../fixture.jpg"
    data["frames"][0]["review_status"] = "REVIEWED_TRACK_ID"
    draft, review = tmp_path / "draft.json", tmp_path / "review.json"
    draft.write_text(json.dumps(data))
    review.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="provenance"):
        validate_review(draft, review)
