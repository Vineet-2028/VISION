"""Compact diagnostics retain causal identity without copying bounded histories."""

import importlib
import json
from dataclasses import asdict
from pathlib import Path

import pytest
from test_event_lineage import update
from test_picodet_semantics import observation
from test_tracking import detection, tracker
from test_tracking import update as track_update

from perception_lab.detection import Detection, ObjectClass
from perception_lab.event_lineage import attach_event_lineage


@pytest.fixture
def compact(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    return importlib.import_module("alpha_trace").compact_alpha


def test_compact_decision_retains_exact_lineage_and_authorization(compact, geometry):
    decision = attach_event_lineage(update(geometry)).selected[0]
    encoded = compact(decision)
    assert json.loads(json.dumps(encoded["lineage"])) == json.loads(
        json.dumps(asdict(decision.lineage))
    )
    assert encoded["source_observation_ns"] == decision.source_observation_ns
    assert encoded["semantic_authorization_reason"] == decision.semantic_authorization_reason


def test_raw_detector_scores_and_hashes_retained_only_at_observation_origin(compact):
    obs = observation(0)
    item = Detection(0, "unknown", ObjectClass.UNKNOWN, obs.region_confidence, obs.bbox, obs)
    encoded = compact(item)["entity_observation"]
    assert encoded["concept"]["confidence"] == obs.concept.confidence
    assert encoded["concept"]["calibration_status"] == "UNCALIBRATED"
    assert encoded["provider_configuration_sha256"] == obs.provider_configuration_sha256
    assert encoded["orientation_transform_sha256"] == obs.orientation_transform_sha256
    assert compact(obs) == {
        "observation_id": obs.observation_id,
        "source_frame": compact(obs.source_frame),
    }


def test_compact_track_does_not_serialize_history_or_change_prediction_freshness(compact):
    state = tracker()
    track_update(state, 0, [detection()])
    track_update(state, 100, [detection(11)])
    predicted = track_update(state, 150).tracks[0]
    encoded = compact(predicted)
    assert "history" not in encoded
    assert encoded["observation_status"] == "PREDICTED"
    assert encoded["latest_observed_ns"] == 100_000_000
    assert encoded["state_ns"] == 150_000_000
    assert len(json.dumps(encoded)) < len(json.dumps(asdict(predicted)))
