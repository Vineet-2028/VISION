"""Forensic ledgers distinguish missing telemetry from absent semantic evidence."""

import importlib
from dataclasses import dataclass
from pathlib import Path

import pytest


@pytest.fixture
def ledger(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    return importlib.import_module("semantic_event_ledger")


def event():
    identity = {"source_id": "test", "sequence": 1, "observation_ns": 10}
    entity = {"session_id": "test", "serial": 1}
    box = {"x1": 0, "y1": 0, "x2": 10, "y2": 10}
    frozen = {
        "alert_id": "a",
        "entity_id": entity,
        "track_id": entity,
        "source_observation_ns": 10,
        "publication_frame": identity,
    }
    output = {
        "intent": {
            "alert_id": "a",
            "entity_id": entity,
            "source_observation_ns": 10,
            "event_id": "event",
            "reason_codes": ["SEMANTICS_UNAVAILABLE"],
        },
        "presentation": {"speech_text": "Object."},
    }
    row = {
        "identity": identity,
        "detector": {"identity": identity, "detections": [{"class_name": "car", "box": box}]},
        "tracks": {
            "tracks": [
                {
                    "track_id": entity,
                    "category": "CAR",
                    "observation_status": "OBSERVED",
                    "latest_observed_bbox": box,
                    "observation_age_ns": 0,
                }
            ]
        },
        "world": {"entities": [{"entity_id": entity, "category": "CAR"}]},
        "attention_decision_set": {"selected": [{"entity_id": entity}]},
    }
    return row, output, frozen


def test_ledger_does_not_turn_omitted_metadata_into_a_claimed_failure(ledger):
    row, output, frozen = event()
    result = ledger.event_ledger(row, output, frozen)
    assert len(result["stages"]) == 8
    assert result["stages"][0]["raw_concept"] == "car"
    assert result["stages"][5]["rejection_reason"] == "SEMANTIC_EVIDENCE_OMITTED_FROM_TRACE"
    assert result["first_semantic_loss_stage"] == "UNKNOWN"
    assert result["first_confirmed_unavailable_stage"] == "ALERT_INTENT_SEMANTIC"
    row["attention_decision_set"]["selected"][0]["semantic_evidence"] = None
    assert (
        ledger.event_ledger(row, output, frozen)["stages"][5]["rejection_reason"]
        == "SEMANTICS_UNAVAILABLE"
    )


def test_ledger_rejects_wrong_identity_and_ambiguous_detector_association(ledger):
    row, output, frozen = event()
    row["detector"]["detections"] *= 2
    assert ledger.event_ledger(row, output, frozen)["stages"][0]["raw_concept"] is None
    output["intent"]["source_observation_ns"] = 11
    with pytest.raises(ValueError, match="association"):
        ledger.event_ledger(row, output, frozen)


def test_ledger_rejects_changed_trace_or_missing_population(ledger, tmp_path):
    trace = tmp_path / "trace.jsonl"
    trace.write_text("")
    population = {"alerts": [{"alert_id": str(i)} for i in range(60)], "updates_sha256": "0" * 64}
    with pytest.raises(ValueError, match="hash"):
        ledger.build(population, trace)
    population["updates_sha256"] = ledger.digest(trace)
    with pytest.raises(ValueError, match="Incomplete"):
        ledger.build(population, trace)


def test_new_trace_retains_semantic_evidence_and_provider_provenance(ledger):
    compact = importlib.import_module("v0_replay").compact

    @dataclass
    class Evidence:
        concept: str
        provenance: tuple[str, ...]

    @dataclass
    class Decision:
        semantic_evidence: Evidence | None

    assert compact(Decision(Evidence("bollard", ("provider-version",)))) == {
        "semantic_evidence": {"concept": "bollard", "provenance": ("provider-version",)}
    }
    assert compact(Decision(None)) == {"semantic_evidence": None}
