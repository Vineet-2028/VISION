"""Residual screening must follow causal identity even when delivery is delayed."""

import importlib
from copy import deepcopy
from pathlib import Path

import pytest


@pytest.fixture
def residual(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    return importlib.import_module("alpha_residuals")


def rows():
    entity = {"session_id": "s", "serial": 1}
    source = {"source_id": "v", "sequence": 1, "observation_ns": 30}
    observation = {"observation_id": "o", "source_frame": source}
    lineage = {
        "attention_event_id": "event",
        "entity_instance_id": entity,
        "observation_id": "o",
        "origin_source_identity": source,
    }
    first = {
        "schema_version": 2,
        "world": {"entities": [{"entity_id": entity, "entity_observation": observation}]},
        "attention_decision_set": {"selected": [{"entity_id": entity, "lineage": lineage}]},
    }
    later = {
        "schema_version": 2,
        "world": {"entities": []},
        "alert_output_set": {
            "outputs": [
                {
                    "delivered": True,
                    "intent": {"alert_id": "alert", "entity_id": entity, "lineage": lineage},
                    "presentation": {"semantic_level": "GENERIC", "lineage": lineage},
                }
            ]
        },
    }
    return [first, later]


def test_delayed_delivery_uses_original_source_not_delivery_frame(residual):
    report = residual.collect(rows())
    assert report["generic_outputs"] == report["delivered_outputs"] == 1
    assert report["targets"][0]["source_observation"]["source_frame"]["observation_ns"] == 30
    assert report["targets"][0]["association"] == "EXACT_IMMUTABLE_EVENT_LINEAGE"


def test_no_matching_event_must_not_be_replaced_by_nearest_box(residual):
    with pytest.raises(ValueError, match="No exact causal"):
        residual.collect(rows()[1:])
    data = rows()
    data[0]["world"]["entities"] *= 2
    with pytest.raises(ValueError, match="one exact"):
        residual.collect(data)


def test_duplicate_delivery_and_tampered_origin_rejected(residual):
    data = rows()
    with pytest.raises(ValueError, match="Duplicate delivered"):
        residual.collect([*data, data[-1]])
    data = deepcopy(rows())
    data[0]["world"]["entities"][0]["entity_observation"]["observation_id"] = "other"
    with pytest.raises(ValueError, match="lineage disagree"):
        residual.collect(data)


def test_residual_candidate_population_cannot_claim_fixed_denominators(residual):
    candidate = importlib.import_module("v02_candidate_population")
    report = residual.collect(rows())
    report["status"] = "EXACT_LINEAGE_RESIDUAL_SCREENING_SET"
    assert candidate.residual_targets(report) == [30]
    report["targets"] *= 2
    with pytest.raises(ValueError, match="identities/count"):
        candidate.residual_targets(report)


def test_specific_presentations_still_require_valid_lineage(residual):
    data = rows()
    presentation = data[-1]["alert_output_set"]["outputs"][0]["presentation"]
    presentation["semantic_level"] = "SPECIFIC"
    report = residual.collect(data)
    assert report["generic_outputs"] == 0
    assert report["delivered_lineages_verified"] == 1
    presentation["lineage"] = None
    with pytest.raises(ValueError, match="matching immutable lineage"):
        residual.collect(data)


def test_selected_entity_must_match_lineage_even_without_source_observation(residual):
    data = rows()
    entity = data[0]["world"]["entities"][0]
    entity["entity_observation"] = None
    # Keep the selected decision/world join valid, but corrupt its lineage identity.
    decision = data[0]["attention_decision_set"]["selected"][0]
    decision["lineage"]["entity_instance_id"] = {"session_id": "other", "serial": 1}
    with pytest.raises(ValueError, match="Selected entity disagrees"):
        residual.collect(data)


def test_fusion_diagnostics_require_matching_policy_and_distinct_source_frames(residual):
    from perception_lab.config import canonical_hash
    from perception_lab.track_semantics import SemanticFusionConfig

    state = {
        "configuration_hash": canonical_hash(
            {
                "policy_version": "bounded-track-semantics-v2",
                "config": SemanticFusionConfig().model_dump(),
            }
        ),
        "quality": "UNSTABLE",
        "evidence": [
            {
                "observation": {
                    "source_frame": {"sequence": 1, "observation_ns": 10},
                    "provider_id": "primary",
                    "model_version": "v1",
                    "provider_configuration_sha256": "a",
                    "concept": {"confidence": 0.1},
                }
            }
        ],
    }
    state["evidence"] *= 3
    result = residual.semantic_blockers(state, 20)
    assert result["distinct_source_frames"] == 1
    assert result["blockers"] == ["INSUFFICIENT_DETECTOR_UPDATES", "BELOW_SCORE_SUPPORT"]
    second = deepcopy(state["evidence"][0])
    second["observation"]["provider_configuration_sha256"] = "b"
    state["evidence"].append(second)
    assert "CONFIG_STREAM_SPLIT" in residual.semantic_blockers(state, 20)["blockers"]
    second["observation"]["provider_id"] = "other"
    assert "PROVIDER_STREAM_SPLIT" in residual.semantic_blockers(state, 20)["blockers"]
    state.pop("evidence")
    state["evidence_count"] = 2
    assert residual.semantic_blockers(state, 20)["blockers"] == ["INSUFFICIENT_DETECTOR_UPDATES"]
    state["evidence_count"] = 3
    assert residual.semantic_blockers(state, 20)["blockers"] == ["UNKNOWN"]
    state["configuration_hash"] = "unrecognized-policy"
    assert residual.semantic_blockers(state, 20) == {
        "policy_verified": False,
        "blockers": ["UNKNOWN"],
    }


def test_later_primary_stability_is_separate_from_generic_presentation_and_track_replacement(
    residual,
):
    data = rows()
    decision = data[0]["attention_decision_set"]["selected"][0]
    decision["state_timestamp"] = 30
    later = {
        "schema_version": 2,
        "identity": {"observation_ns": 50},
        "world": {
            "entities": [
                {
                    "entity_id": deepcopy(decision["entity_id"]),
                    "track_semantics": {"quality": "STABLE", "valid_until_ns": 100},
                }
            ]
        },
    }
    report = residual.collect([*data, later])
    assert report["generic_outputs"] == 1
    target = report["targets"][0]
    assert target["first_later_specific_stable_ns"] == 50
    assert target["temporal_classification"] == "BECAME_STABLE_CONTINUOUSLY"
    assert target["screenable"]
    later["world"]["entities"][0]["entity_id"]["serial"] = 2
    target = residual.collect([*data, later])["targets"][0]
    assert target["first_later_specific_stable_ns"] is None
    assert target["screenable"]
