"""Benchmark integrity checks independent of heavyweight model inference."""

import hashlib
import importlib
import json
from pathlib import Path

import av
import pytest
from test_video import generate_video


@pytest.fixture
def tooling(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    return importlib.import_module("v02_score_population"), importlib.import_module(
        "v02_candidate_population"
    )


def test_exact_frame_never_substitutes_nearby_vfr_frame(tooling, tmp_path):
    _, candidate = tooling
    path = tmp_path / "vfr.mkv"
    generate_video(path)
    with path.open("rb") as stream, av.open(stream) as container:
        video = container.streams.video[0]
        assert candidate.exact_frame(container, video, 120_000_000).shape == (6, 8, 3)
        with pytest.raises(ValueError, match="Exact source frame unavailable"):
            candidate.exact_frame(container, video, 80_000_000)
    path.unlink()


def test_unknown_region_is_not_no_entity(tooling):
    scorer, _ = tooling
    result = scorer.match(
        [{"box": [0, 0, 10, 10], "concept": None, "confidence": 0.9}], [0, 0, 10, 10]
    )
    assert result["entity_match"] and result["specific_concept"] is None
    assert not scorer.match([], [0, 0, 10, 10])["entity_match"]


def test_candidate_budget_rejects_deadline_and_low_memory(tooling):
    _, candidate = tooling
    candidate.check_budget(9, 10, 2 * 1024**3)
    with pytest.raises(RuntimeError, match="time cap"):
        candidate.check_budget(10, 10, 2 * 1024**3)
    with pytest.raises(RuntimeError, match="RAM"):
        candidate.check_budget(9, 10, 2 * 1024**3 - 1)


def test_score_preserves_all_denominators_and_rejects_missing_frames(tooling):
    scorer, _ = tooling
    alert = {
        "source_observation_ns": 0,
        "entity_observed_ns": 0,
        "entity_observation_status": "OBSERVED",
        "entity_box": {"x1": 0, "y1": 0, "x2": 10, "y2": 10},
    }
    population = {
        "alerts": [{**alert, "alert_id": str(i)} for i in range(60)],
        "events": [
            {
                "event_id": str(i),
                "observations": [{"observation_ns": 0, "reference_box": [0, 0, 10, 10]}],
            }
            for i in range(188)
        ],
    }
    empty = scorer.score(population, {0: []})
    assert empty["alerts"]["generic_count"] == 60
    assert empty["events"]["entity_covered"] == 0
    assert len(empty["events"]["rows"]) == 188
    with pytest.raises(ValueError, match="every source frame"):
        scorer.score(population, {})


def test_teacher_asset_hash_and_metadata_validation(tooling, tmp_path):
    verify = importlib.import_module("acquire_offline_teacher").verify
    path = tmp_path / "asset"
    path.write_bytes(b"model")
    record = {"name": "asset", "bytes": 5, "sha256": hashlib.sha256(b"model").hexdigest()}
    assert verify(path, record) == record["sha256"]
    path.write_bytes(b"wrong")
    with pytest.raises(ValueError, match="SHA256"):
        verify(path, record)
    with pytest.raises(ValueError, match="git object"):
        verify(path, {"name": "asset", "bytes": 5, "git_blob_sha1": "0" * 40})


def test_teacher_resume_rejects_gaps_duplicates_and_wrong_status(tooling, tmp_path):
    read_prefix = importlib.import_module("v02_teacher_population").read_prefix
    path = tmp_path / "checkpoint.jsonl"
    row = {
        "source_ns": 10,
        "call_ns": 20,
        "rss_bytes": 100,
        "status": "MODEL_PSEUDO_LABEL",
        "regions": [],
    }
    path.write_text(json.dumps(row) + "\n")
    assert read_prefix(path, [10, 20]) == [row]
    with pytest.raises(ValueError, match="ordered population prefix"):
        read_prefix(path, [0, 10, 20])
    path.write_text((json.dumps(row) + "\n") * 2)
    with pytest.raises(ValueError, match="ordered population prefix"):
        read_prefix(path, [10, 20])
    path.write_text(json.dumps({**row, "status": "GROUND_TRUTH"}) + "\n")
    with pytest.raises(ValueError, match="provenance"):
        read_prefix(path, [10])
