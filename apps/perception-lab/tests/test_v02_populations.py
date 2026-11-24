"""Fixed denominators must fail closed, and publication time is not source time."""

import importlib
import json
from pathlib import Path

import pytest


def test_population_preserves_source_identity_and_all_reference_observations(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    extract = importlib.import_module("v02_populations").populations
    (tmp_path / "manifest.json").write_text(
        json.dumps({"status": "COMPLETE", "source_sha256": "a" * 64})
    )
    reference = tmp_path / "references.json"
    reference.write_text(
        json.dumps(
            {
                "frames": [
                    {
                        "clip_id": "clip",
                        "observation_ns": t,
                        "width": 100,
                        "height": 100,
                        "annotations": [
                            {"ground_truth_track_id": 1, "label": "PERSON", "box": [40, 40, 60, 90]}
                        ],
                    }
                    for t in (0, 10)
                ]
            }
        )
    )
    entity_id = {"session_id": "s", "serial": 1}
    row = {
        "identity": {"sequence": 2, "observation_ns": 20},
        "world": {
            "entities": [
                {
                    "entity_id": entity_id,
                    "source_track_id": entity_id,
                    "observation_age_ns": 10,
                    "observation_status": "PREDICTED",
                    "box": {},
                }
            ]
        },
        "alert_output_set": {
            "outputs": [
                {
                    "delivered": True,
                    "intent": {
                        "alert_id": "alert",
                        "event_id": "event",
                        "entity_id": entity_id,
                        "source_observation_ns": 0,
                    },
                    "presentation": {"speech_text": "Object."},
                }
            ]
        },
    }
    trace = tmp_path / "updates.jsonl"
    trace.write_text(json.dumps(row) + "\n")
    result = extract(tmp_path, reference, alert_count=1, event_count=1)
    assert len(result["events"][0]["observations"]) == 2
    alert = result["alerts"][0]
    assert alert["source_observation_ns"] == 0
    assert alert["entity_observed_ns"] == 10
    assert alert["publication_frame"]["observation_ns"] == 20
    assert alert["entity_observation_status"] == "PREDICTED"
    with pytest.raises(ValueError, match="alert denominator"):
        extract(tmp_path, reference, alert_count=2, event_count=1)
    with pytest.raises(ValueError, match="event denominator"):
        extract(tmp_path, reference, alert_count=1, event_count=2)
    trace.write_text((json.dumps(row) + "\n") * 2)
    with pytest.raises(ValueError, match="Duplicate"):
        extract(tmp_path, reference, alert_count=2, event_count=1)
