import importlib.util
import json
from dataclasses import asdict
from types import SimpleNamespace

import pytest
from conftest import ROOT

from perception_lab.detection import Box, Detection, ObjectClass
from perception_lab.detector_benchmark import accuracy


def tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def data():
    predictions = (
        Detection(0, "person", ObjectClass.PERSON, 0.9, Box(0, 0, 2, 2)),
        Detection(0, "person", ObjectClass.PERSON, 0.8, Box(0, 0, 2, 2)),
        Detection(0, "person", ObjectClass.PERSON, 0.4, Box(5, 5, 7, 7)),
        Detection(0, "person", ObjectClass.PERSON, 0.2, Box(8, 8, 9, 9)),
    )
    entries = [
        {
            "image_id": 1,
            "width": 10,
            "height": 10,
            "annotations": [
                {
                    "label": "PERSON",
                    "box": [0, 0, 2, 2],
                    "ignore": False,
                    "crowd": False,
                    "occluded": None,
                    "truncated": None,
                    "difficulty": "UNKNOWN",
                },
                {
                    "label": "PERSON",
                    "box": [5, 5, 7, 7],
                    "ignore": False,
                    "crowd": True,
                    "occluded": None,
                    "truncated": None,
                    "difficulty": "UNKNOWN",
                },
            ],
        }
    ]
    report = {
        "status": "MEASURED_LOCALLY",
        "image_ids": [1],
        "candidate": {},
        "configuration": {"confidence_floor": 0.01},
        "dataset_sha256": "0" * 64,
        "predictions": [{"image_id": 1, "detections": [asdict(p) for p in predictions]}],
    }
    return entries, predictions, report


def test_efficient_sweep_equals_full_matching_at_every_threshold():
    entries, predictions, report = data()
    result = tool("qualify_detectors").analyze(report, {"images": entries})
    for point in result["curves"]["P0"]:
        expected = accuracy(entries, [predictions], point["threshold"], 0.5)
        assert (point["tp"], point["fp"], point["fn"]) == (
            expected["tp"],
            expected["fp"],
            expected["fn"],
        )
    assert result["curves"]["P0"][0]["fp"] == 2  # duplicate + unmatched; crowd absorbed


@pytest.mark.parametrize("change", [{"status": "FAILED"}, {"image_ids": [2]}])
def test_failed_or_wrong_frame_run_cannot_become_accuracy(change):
    entries, _, report = data()
    report.update(change)
    with pytest.raises(ValueError):
        tool("qualify_detectors").analyze(report, {"images": entries})


def test_group_localization_and_scenario_denominators():
    entries, predictions, _ = data()
    entries[0].update(motion="HIGH", lighting="LOW_LIGHT")
    result = accuracy(entries, [predictions], 0.5, 0.5)
    assert result["bottom_center_by_group"]["PERSON"] == {
        "matched_count": 1,
        "mean_normalized_error": 0,
    }
    assert result["bottom_center_by_group"]["BICYCLE"]["mean_normalized_error"] is None
    assert result["slices"]["motion"]["HIGH"] == {
        "tp": 1,
        "fp": 1,
        "fn": 0,
        "frames": 1,
        "recall": 1,
    }


def test_local_export_and_coco_import_never_auto_approve_annotations(tmp_path):
    from test_video import generate_video

    video = tmp_path / "fixture.mkv"
    generate_video(video)
    output = tmp_path / "frames"
    workflow = tool("evaluation_dataset")
    workflow.export(
        SimpleNamespace(
            video=video,
            output=output,
            sequence="fixture",
            source="TEST_ONLY",
            license="TEST_ONLY",
            split="TEST",
            fps=2.0,
        )
    )
    draft_path = output / "manifest.draft.json"
    draft = json.loads(draft_path.read_text())
    assert len(draft["images"]) == 1
    assert draft["images"][0]["observation_ns"] == 0
    assert not draft["images"][0]["annotations_reviewed"]
    annotations = output / "coco.json"
    annotations.write_text(
        json.dumps(
            {
                "images": [{"id": 42, "file_name": "frame-000000.ppm", "width": 8, "height": 6}],
                "categories": [{"id": 99, "name": "person"}],
                "annotations": [{"image_id": 42, "category_id": 99, "bbox": [1, 1, 2, 3]}],
            }
        )
    )
    imported = output / "imported.json"
    workflow.import_coco(
        SimpleNamespace(manifest=draft_path, annotations=annotations, output=imported)
    )
    result = json.loads(imported.read_text())
    assert result["images"][0]["annotations"][0]["label"] == "PERSON"
    assert result["images"][0]["annotations"][0]["box"] == [1, 1, 3, 4]
    assert not result["images"][0]["annotations_reviewed"]
    video.unlink()  # Decoder handles close even after two-pass sampling.


@pytest.mark.parametrize("invalid", ["false", "0", 2, None])
def test_coco_flags_cannot_silently_hide_ground_truth(invalid):
    with pytest.raises(ValueError):
        tool("evaluation_dataset").coco_flag(invalid)
