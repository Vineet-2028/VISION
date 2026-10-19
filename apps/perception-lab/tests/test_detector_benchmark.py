import json
import subprocess
import sys
from dataclasses import replace

import pytest
from conftest import records

from perception_lab import detector_benchmark as benchmark
from perception_lab.components import NoOpDetector
from perception_lab.contracts import ComponentProvenance
from perception_lab.detection import DetectionBatch
from perception_lab.detector_runtime import UltralyticsDetector, file_hash
from perception_lab.sources import SyntheticSource


def test_gpu_sync_wrapper_is_required_only_on_gpu():
    from types import SimpleNamespace

    from perception_lab.rtdetr_runtime import RtDetrDetector

    calls = []
    detector = object.__new__(RtDetrDetector)
    detector.torch = SimpleNamespace(cuda=SimpleNamespace(synchronize=lambda: calls.append("sync")))
    detector.device = "cpu"
    detector.synchronize()
    assert calls == []
    detector.device = "cuda:0"
    detector.synchronize()
    assert calls == ["sync"]


def test_empty_success_is_distinct_from_noop_and_failure(make_pipeline):
    class EmptyDetector(NoOpDetector):
        def detect(self, image, identity):
            return DetectionBatch(identity, (), self.provenance, image.mapping.fingerprint, 2, 3)

    pipeline, recorder = make_pipeline({"record_session": True}, detector=EmptyDetector())
    pipeline.run(SyntheticSource(iter([0, 1, 10])))
    results = [r for r in records(recorder) if r["type"] == "frame_result"]
    assert results[0]["detector"]["identity"]["observation_ns"] == 0
    assert results[1]["detector"] is None  # independently scheduled, not stale reuse
    assert results[2]["detector"]["identity"]["observation_ns"] == 10
    assert results[0]["components"][0]["status"] == "SUCCESS_EMPTY"
    assert recorder.manifest["summary"]["frame_counts"]["failed"] == 0


def test_component_overrun_is_measured_without_claiming_hard_cancellation(
    make_pipeline, monkeypatch
):
    now = [0]
    monkeypatch.setattr("perception_lab.sources.processing_ns", lambda: now[0])

    class SlowTestDetector(NoOpDetector):
        def detect(self, image, identity):
            now[0] += 50
            return None

    pipeline, recorder = make_pipeline(
        {"record_session": True, "intervals_ns": {"detector": 10}},
        detector=SlowTestDetector(),
        clock=lambda: now[0],
    )
    pipeline.run(SyntheticSource(iter([0])))
    result = next(r for r in records(recorder) if r["type"] == "frame_result")
    assert result["components"][0]["overrun_ns"] == 40
    assert result["components"][0]["status"] == "NO_OUTPUT"


def test_real_benchmark_image_preparation_uses_unknown_calibration(tmp_path):
    path = tmp_path / "fixture.ppm"
    path.write_bytes(b"P6\n8 6\n255\n" + bytes(8 * 6 * 3))
    image, identity = benchmark.prepare(
        {"path": "fixture.ppm", "sha256": file_hash(path), "width": 8, "height": 6}, tmp_path, 7
    )
    assert image.pixels.shape == (6, 8, 3)
    assert identity.sequence == identity.observation_ns == 7
    assert image.mapping.inverse(4, 3) == (4, 3)
    _, video_identity = benchmark.prepare(
        {
            "path": "fixture.ppm",
            "sha256": file_hash(path),
            "width": 8,
            "height": 6,
            "sequence_id": "walk-clip",
            "observation_ns": 700_000_000,
        },
        tmp_path,
        8,
    )
    assert video_identity.source_id == "walk-clip"
    assert video_identity.observation_ns == 700_000_000


def test_untrusted_weight_hash_rejected_before_vendor_import(tmp_path, monkeypatch):
    weights = tmp_path / "unsafe.pt"
    weights.write_bytes(b"not a checkpoint")

    def forbidden(*args):
        pytest.fail("Vendor import before hash verification")

    monkeypatch.setattr("perception_lab.detector_runtime.importlib.import_module", forbidden)
    with pytest.raises(ValueError, match="hash mismatch"):
        UltralyticsDetector(weights, "0" * 64)


def test_vendor_settings_parent_exists_before_import(tmp_path, monkeypatch):
    import os
    from pathlib import Path

    weights = tmp_path / "trusted-test.pt"
    weights.write_bytes(b"test only")
    monkeypatch.setattr("perception_lab.detector_runtime.enforce_offline", lambda: None)
    monkeypatch.setenv("YOLO_CONFIG_DIR", "unused")

    def stop_before_vendor(name):
        assert name == "ultralytics"
        assert Path(os.environ["YOLO_CONFIG_DIR"]) == tmp_path / "runtime-settings"
        assert Path(os.environ["YOLO_CONFIG_DIR"]).is_dir()
        raise RuntimeError("test stopped before vendor import")

    monkeypatch.setattr(
        "perception_lab.detector_runtime.importlib.import_module", stop_before_vendor
    )
    with pytest.raises(RuntimeError, match="test stopped"):
        UltralyticsDetector(weights, file_hash(weights))


def test_benchmark_warmup_excluded_and_all_images_share_policy(tmp_path, monkeypatch, geometry):
    from perception_lab.config import PreprocessConfig
    from perception_lab.preprocessing import BasicPreprocessor

    frame = next(iter(SyntheticSource(iter([0]))))
    prepared = BasicPreprocessor(geometry, PreprocessConfig()).prepare(frame)
    calls = []

    class TestOnlyDetector:
        provenance = ComponentProvenance("test-only", "detector")
        last_timings_ns = {"inference": 7}

        def __init__(self, *args, **kwargs):
            pass

        def detect(self, image, identity):
            calls.append(identity.sequence)
            return DetectionBatch(identity, (), self.provenance, "0" * 64, 7, 0)

    monkeypatch.setattr(benchmark, "UltralyticsDetector", TestOnlyDetector)
    monkeypatch.setattr(
        benchmark, "prepare", lambda entry, base, i: (prepared, replace(frame.identity, sequence=i))
    )
    monkeypatch.setattr(benchmark, "version", lambda name: "test-runtime")
    dataset = tmp_path / "dataset.json"
    dataset.write_text(
        json.dumps(
            {
                "dataset": "test-only",
                "images": [
                    {"image_id": i, "annotations": [], "width": 8, "height": 6} for i in range(2)
                ],
            }
        )
    )
    weights = tmp_path / "test.pt"
    weights.write_bytes(b"test")
    output = tmp_path / "report.json"
    assert (
        benchmark.main(
            [
                "--dataset",
                str(dataset),
                "--weights",
                str(weights),
                "--sha256",
                "0" * 64,
                "--output",
                str(output),
                "--warmup",
                "3",
            ]
        )
        == 0
    )
    result = json.loads(output.read_text())
    assert calls == [0, 0, 0, 0, 0, 1]
    assert result["steady_latency_ns"]["inference"]["count"] == 2
    assert result["steady_latency_ns"]["inference"]["p99_ns"] == 7
    assert result["configuration"]["batch"] == 1
    assert len(result["accuracy"]) == 16
    assert not result["qualified_for_production"]


def test_failed_candidate_has_no_accuracy_or_successful_empty_output(tmp_path):
    output = tmp_path / "failed.json"
    assert (
        benchmark.main(
            [
                "--dataset",
                str(tmp_path / "missing.json"),
                "--weights",
                str(tmp_path / "missing.pt"),
                "--sha256",
                "0" * 64,
                "--output",
                str(output),
            ]
        )
        == 1
    )
    result = json.loads(output.read_text())
    assert result["status"] == "FAILED"
    assert "accuracy" not in result and "predictions" not in result
    assert str(tmp_path) not in output.read_text()


def test_offline_worker_blocks_python_network_before_vendor_import():
    script = (
        "import socket; from perception_lab.offline import enforce_offline; enforce_offline(); "
        "socket.getaddrinfo('example.com', 443)"
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode != 0
    assert "NETWORK_DISABLED_FOR_LOCAL_MODEL_WORKER" in result.stderr


def test_class_scenario_aggregation_keeps_unknown_labels_and_denominators():
    from perception_lab.detection import Box, Detection, ObjectClass

    annotation = {
        "label": "PERSON",
        "box": [0, 0, 10, 10],
        "ignore": False,
        "crowd": False,
        "occluded": None,
        "truncated": None,
        "difficulty": "UNKNOWN",
    }
    entries = [
        {
            "image_id": 1,
            "width": 100,
            "height": 100,
            "scenario": "sidewalk",
            "annotations": [annotation],
        },
        {"image_id": 2, "width": 100, "height": 100, "annotations": [annotation]},
    ]
    prediction = Detection(0, "person", ObjectClass.PERSON, 0.8, Box(0, 0, 6, 10))
    result = benchmark.accuracy(entries, [(prediction,), ()], 0.25, 0.5)
    assert result["p0_micro_recall"] == 0.5
    assert result["classes"]["PERSON"] == {"tp": 1, "fp": 0, "fn": 1, "recall": 0.5}
    assert result["classes"]["DOG"]["recall"] is None
    assert result["slices"]["scenario"]["sidewalk"]["recall"] == 1
    assert result["slices"]["scenario"]["UNKNOWN"]["recall"] == 0
    assert result["slices"]["lighting"]["UNKNOWN"]["frames"] == 2
    assert result["error_review"][0]["low_iou_matches"][0]["iou"] == 0.6
