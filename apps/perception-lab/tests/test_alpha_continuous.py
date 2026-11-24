"""Admission must never depend on target events or detector success."""

import importlib
import json
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def admission(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    return importlib.import_module("alpha_continuous_replay").Admission


def test_continuous_admission_preserves_source_pts_without_target_injection(admission):
    schedule = admission(200, 1000)
    pts = [0, 33, 99, 201, 233, 399, 433, 599, 601, 799, 801, 999, 1000]
    assert [t for t in pts if schedule.accept(t)] == [0, 201, 433, 601, 801]


def test_gap_does_not_invent_frames_or_reset_deadline(admission):
    schedule = admission(200, 2000)
    assert [t for t in [0, 999, 1000, 1100, 1200] if schedule.accept(t)] == [0, 999, 1000, 1200]


def test_duplicate_or_regressing_pts_rejected(admission):
    for stamp in [0, -1]:
        schedule = admission(200, 1000)
        schedule.accept(0)
        with pytest.raises(ValueError, match="monotonic"):
            schedule.accept(stamp)


@pytest.fixture
def pair(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    module = importlib.import_module("alpha_compare_continuous")
    paths = []
    for arm in ("A", "B"):
        folder = tmp_path / arm
        folder.mkdir()
        row = {
            "schema_version": 2,
            "identity": {"source_id": "source", "sequence": 1, "observation_ns": 200},
            "tracks": {"session_id": arm, "tracks": [{"serial": 1}]},
            "world": {"entities": []},
            "detector": None,
            "corridor_analysis": None,
            "trajectory_set": None,
            "interaction_analysis": None,
            "risk_assessment_set": None,
            "attention_decision_set": None,
        }
        (folder / "updates.jsonl").write_text(json.dumps(row) + "\n")
        summary = {
            "status": "COMPLETE_CONTINUOUS_OFFLINE_PRESENTATION_ABLATION",
            "runtime": {"providers": ["CPUExecutionProvider"]},
            "writer_drops": 0,
            "summary": {
                "failure": None,
                "summary": {"frame_counts": {"processed": 1, "failed": 0, "dropped": 0}},
            },
            "arm": arm,
            "source_sha256": "source",
            "admission_sha256": "schedule",
            "seconds": 1,
            "admitted": 1,
            "ontology_sha256": "ontology",
            "updates_sha256": module.digest(folder / "updates.jsonl"),
        }
        (folder / "continuous-summary.json").write_text(json.dumps(summary))
        (folder / "configuration.json").write_text(
            json.dumps(
                {
                    "output": arm,
                    "semantic_presentation_enabled": arm == "B",
                    "threshold": 0.5,
                }
            )
        )
        (folder / "source-manifest.json").write_text('{"runtime": "same"}')
        paths.append(folder)
    return module, paths


@pytest.mark.parametrize("fault", ["incomplete", "failed", "dropped", "empty", "runtime"])
def test_pair_rejects_failed_empty_or_runtime_mismatched_runs(pair, fault):
    module, paths = pair
    path = paths[1] / "continuous-summary.json"
    summary = json.loads(path.read_text())
    if fault == "incomplete":
        summary["status"] = "INCOMPLETE"
    elif fault == "empty":
        summary["admitted"] = 0
    elif fault == "runtime":
        summary["runtime"] = {"providers": ["CUDAExecutionProvider"]}
    else:
        summary["summary"]["summary"]["frame_counts"][fault] = 1
    path.write_text(json.dumps(summary))
    with pytest.raises(ValueError, match="failure-free|prerequisite mismatch: runtime"):
        module.compare(*paths)


def test_pair_rejects_missing_stage_even_when_trace_hash_matches(pair):
    module, paths = pair
    for folder in paths:
        path = folder / "updates.jsonl"
        row = json.loads(path.read_text())
        del row["risk_assessment_set"]
        path.write_text(json.dumps(row) + "\n")
        summary_path = folder / "continuous-summary.json"
        summary = json.loads(summary_path.read_text())
        summary["updates_sha256"] = module.digest(path)
        summary_path.write_text(json.dumps(summary))
    with pytest.raises(ValueError, match="physical stage missing"):
        module.compare(*paths)


def test_historical_markers_remain_explicitly_unresolved_without_shared_lineage(pair):
    module, _ = pair
    population = {
        "alerts": [{"alert_id": str(i)} for i in range(60)],
        "events": [{"event_id": str(i)} for i in range(188)],
    }
    result = module.historical_population_status(population)
    assert result["alerts"]["unresolved"] == 60
    assert result["events"]["unresolved"] == 188
    assert result["alerts"]["corresponded"] == result["events"]["corresponded"] == 0
    assert all(m["current_semantic_state"] is None for m in result["alerts"]["markers"])
    population["alerts"][0]["lineage"] = {"attention_event_id": "supplied"}
    with pytest.raises(ValueError, match="explicit correspondence analysis"):
        module.historical_population_status(population)
    population["alerts"][0].pop("lineage")
    population["events"][-1]["event_id"] = "0"
    with pytest.raises(ValueError, match="denominator/identity"):
        module.historical_population_status(population)


def test_pair_accepts_only_declared_configuration_difference(pair):
    module, paths = pair
    assert module.compare(*paths)["status"] == "PAIRED_PRESENTATION_ABLATION_VERIFIED"
    path = paths[1] / "configuration.json"
    config = json.loads(path.read_text())
    config["threshold"] = 0.4
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="Configurations differ"):
        module.compare(*paths)


def test_pair_rejects_compact_trace_even_with_matching_hash(pair):
    module, paths = pair
    path = paths[1] / "updates.jsonl"
    row = json.loads(path.read_text())
    row.update(schema_version=3, trace_mode="COMPACT_ALPHA_TRACE")
    path.write_text(json.dumps(row) + "\n")
    summary_path = paths[1] / "continuous-summary.json"
    summary = json.loads(summary_path.read_text())
    summary["updates_sha256"] = module.digest(path)
    summary_path.write_text(json.dumps(summary))
    with pytest.raises(ValueError, match="Full schema-2"):
        module.compare(*paths)


def test_pair_rejects_tampered_trace_and_tracks_real_physical_divergence(pair):
    module, paths = pair
    path = paths[1] / "updates.jsonl"
    row = json.loads(path.read_text())
    row["tracks"]["tracks"][0]["serial"] = 2
    path.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        module.compare(*paths)
    summary_path = paths[1] / "continuous-summary.json"
    summary = json.loads(summary_path.read_text())
    summary["updates_sha256"] = module.digest(path)
    summary_path.write_text(json.dumps(summary))
    report = module.compare(*paths)
    assert report["status"] == "PAIR_DIVERGED"
    assert report["nonpresentation_differences"] == {"tracks": 1}


@pytest.mark.parametrize(
    "free,clock,reason",
    [
        (1024**3, 0, "FREE_RAM_RESERVE_REACHED"),
        (4 * 1024**3, 100, "WALL_BUDGET_EXHAUSTED"),
    ],
)
def test_budget_stop_preserves_machine_reason_before_pixel_conversion(
    monkeypatch, tmp_path, free, clock, reason
):
    import psutil

    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    module = importlib.import_module("alpha_continuous_replay")
    video = tmp_path / "source.mp4"
    video.write_bytes(b"test")

    class Container:
        streams = SimpleNamespace(video=[SimpleNamespace(codec_context=SimpleNamespace())])

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def decode(self, _):
            yield SimpleNamespace(pts=0, time_base=Fraction(1, 30), is_corrupt=False)

    monkeypatch.setattr(module.av, "open", lambda *a, **k: Container())
    monkeypatch.setattr(module, "perf_counter_ns", lambda: clock)
    monkeypatch.setattr(psutil, "virtual_memory", lambda: SimpleNamespace(available=free))
    source = module.ContinuousSource(video, "test", 200, 1000, 100)
    with pytest.raises(RuntimeError):
        list(source)
    assert source.failure_code == reason
    assert source.frames == 0 and not source.finished
