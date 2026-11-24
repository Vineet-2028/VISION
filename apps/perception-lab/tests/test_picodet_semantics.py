"""Pinned runtime semantics: source validity never asserts calibrated probability."""

from dataclasses import replace
from pathlib import Path

import pytest
from test_track_semantics import feed, fusion

from perception_lab.concept_resolver import HierarchyConceptResolver
from perception_lab.contracts import ComponentProvenance, FrameIdentity, TimingProvenance
from perception_lab.detection import Box, Detection, DetectionBatch, semantic_class
from perception_lab.edge_runtime import P0_NAMES, PINS
from perception_lab.picodet_semantics import PicoDetSemanticAdapter


def adapter():
    return PicoDetSemanticAdapter(
        HierarchyConceptResolver(
            Path(__file__).resolve().parents[3]
            / "configs/perception/ontology/vision-domain-v2.json"
        ),
        PINS["picodet-s"],
    )


def observation(i, category=2, score=0.85):
    batch = DetectionBatch(
        FrameIdentity("source", i, i * 100_000_000, TimingProvenance.SYNTHETIC),
        (
            Detection(
                category,
                P0_NAMES.get(category, "unknown"),
                semantic_class(P0_NAMES.get(category, "unknown")),
                score,
                Box(0, 0, 10, 10),
            ),
        ),
        ComponentProvenance(
            "PicoDetDetector",
            "detector",
            "picodet-s",
            PINS["picodet-s"],
            configuration_hash="a" * 64,
        ),
        "b" * 64,
        1,
        1,
    )
    return adapter().convert(batch).detections[0].entity_observation


def test_source_validity_and_score_calibration_are_distinct():
    obs = observation(0)
    assert obs.quality == "UNKNOWN"
    assert obs.source_validity == "VALIDATED_RUNTIME_OUTPUT"
    assert obs.concept.calibration_status == "UNCALIBRATED"
    assert obs.concept.score_basis == "DETECTOR_JOINT_SCORE"
    assert obs.objectness_confidence is None
    assert obs.concept.confidence == obs.region_confidence == 0.85
    assert obs.concept.raw_label == "car"
    assert obs.provider_configuration_sha256 == "a" * 64
    assert obs.orientation_transform_sha256 == "b" * 64


def test_valid_uncalibrated_runtime_scores_need_repeated_fresh_associated_support():
    state = fusion()
    assert feed(state, [observation(0), observation(1)]).quality != "STABLE"
    stable = feed(state, [observation(2)])
    assert stable.quality == "STABLE" and stable.selected_concept.raw_label == "car"
    assert stable.calibration_status == "UNCALIBRATED"
    assert state.snapshot(stable.valid_until_ns).selected_concept is None


def test_specific_disagreement_can_have_independently_stable_vehicle_group():
    result = feed(fusion(), [observation(0, 2), observation(1, 7), observation(2, 5)])
    assert result.quality == "UNSTABLE" and result.selected_concept is None
    assert result.group_quality == "STABLE"
    assert result.selected_group.value == "VEHICLE"
    assert result.group_spoken_label == "Vehicle"
    assert result.group_valid_until_ns == 2_200_000_000


def test_prediction_only_ticks_preserve_fresh_specific_and_group_without_new_support():
    state = fusion()
    stable = feed(state, [observation(i) for i in range(3)])
    for now in [300_000_000, 500_000_000, 1_000_000_000]:
        predicted = state.snapshot(now)
        assert predicted.quality == predicted.group_quality == "STABLE"
        assert predicted.selected_concept == stable.selected_concept
        assert predicted.valid_until_ns == stable.valid_until_ns
        assert len(predicted.evidence) == 3
    assert state.snapshot(2_200_000_000).quality == "EXPIRED"


def test_world_prediction_only_updates_keep_semantics_on_the_same_track_generation():
    from test_world_model import model, tracks

    world = model()
    for i in range(3):
        now = i * 100_000_000
        batch = tracks(now)
        obs = replace(
            observation(i), source_frame=batch.identity, bbox=batch.tracks[0].latest_observed_bbox
        )
        batch = replace(batch, tracks=(replace(batch.tracks[0], entity_observation=obs),))
        world.ingest_tracks(batch, now)
    initial = world.snapshot(200_000_000).entities[0]
    for now in [300_000_000, 500_000_000]:
        batch = tracks(now, predicted=True, observed=200_000_000)
        world.ingest_tracks(batch, now)
        entity = world.snapshot(now).entities[0]
        assert entity.entity_id == initial.entity_id
        assert entity.source_track_id == initial.source_track_id
        assert entity.track_semantics.quality == entity.track_semantics.group_quality == "STABLE"
        assert len(entity.track_semantics.evidence) == 3
        assert entity.track_semantics.valid_until_ns == 2_200_000_000
    # A replacement track cannot inherit that evidence.
    replacement = tracks(600_000_000, offset=1)
    world.ingest_tracks(replacement, 600_000_000)
    new = next(e for e in world.snapshot(600_000_000).entities if e.source_track_id.serial == 2)
    assert new.track_semantics is None


def test_missing_semantic_name_preserves_physical_region():
    obs = observation(0, 79)
    assert obs.concept is None
    assert obs.bbox.area == 100 and obs.physical_status == "UNKNOWN_PHYSICAL_OBJECT"
    assert feed(fusion(), [obs]).quality == "UNKNOWN"


def test_scores_from_different_providers_cannot_jointly_authorize_a_concept():
    values = [observation(i) for i in range(3)]
    values[-1] = replace(values[-1], provider_id="other-provider")
    result = feed(fusion(), values)
    assert result.quality != "STABLE" and result.group_quality != "STABLE"


def test_unknown_vocab_is_not_mistaken_for_a_different_joint_score_stream():
    state = fusion()
    feed(state, [observation(i) for i in range(3)])
    result = feed(state, [observation(3, category=79)])
    assert result.quality == "STABLE" and result.group_quality == "STABLE"
    assert result.last_observed_ns == 200_000_000
    assert result.valid_until_ns == 2_200_000_000


def test_provider_configuration_change_cannot_pool_support():
    values = [observation(i) for i in range(3)]
    values[-1] = replace(values[-1], provider_configuration_sha256="c" * 64)
    result = feed(fusion(), values)
    assert result.quality != "STABLE" and result.group_quality != "STABLE"


def test_source_validity_requires_provenance_and_cannot_override_unreliable_evidence():
    obs = observation(0)
    with pytest.raises(ValueError, match="provenance"):
        replace(obs, source_validation_provenance=None)
    result = feed(fusion(), [replace(observation(i), quality="UNRELIABLE") for i in range(3)])
    assert result.quality != "STABLE"


def test_independent_group_is_presented_without_fabricating_a_specific_concept(geometry):
    from test_alerts import batch
    from test_corridor import scene

    from perception_lab.alerts import AlertEngine
    from perception_lab.entity_attention import attach_entity_semantics

    world = scene(geometry)
    entity = world.entities[0]
    state = feed(fusion(), [observation(0, 2), observation(1, 7), observation(2, 5)])
    state = replace(state, track_id=entity.source_track_id)
    world = replace(
        world, state_timestamp=200_000_000, entities=(replace(entity, track_semantics=state),)
    )
    decisions = batch(200_000_000)
    decisions = replace(
        decisions,
        session_id=world.session_id,
        selected=(replace(decisions.selected[0], entity_id=entity.entity_id),),
    )
    authorized = attach_entity_semantics(decisions, world)
    assert authorized.selected[0].semantic_authorization_reason == "AUTHORIZED_STABLE_GROUP"
    assert authorized.selected[0].semantic_evidence.concept is None
    output = AlertEngine().process(authorized, now_ns=200_000_000).outputs[0]
    assert output.presentation.speech_text == "Vehicle."
    assert output.intent.semantic_level == output.presentation.semantic_level == "GROUP"


def test_probe_scorer_distinguishes_semantic_loss_from_silent_attention(monkeypatch):
    import importlib

    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    assess = importlib.import_module("alpha_semantic_score").assess
    identity = {"session_id": "test", "serial": 1}
    row = {
        "world": {
            "entities": [
                {
                    "box": {"x1": 0, "y1": 0, "x2": 10, "y2": 10},
                    "entity_id": identity,
                    "source_track_id": identity,
                    "track_semantics": {
                        "quality": "STABLE",
                        "selected_concept": {"raw_label": "car"},
                    },
                }
            ]
        }
    }
    missing = assess(row, [0, 0, 10, 10])
    assert missing["first_loss_stage"] == "ATTENTION_SEMANTIC"
    decision = {
        "entity_id": identity,
        "decision": "SILENT",
        "reason_codes": ["COOLDOWN"],
        "semantic_evidence": {"concept": "car"},
        "semantic_authorization_reason": "AUTHORIZED_STABLE_SPECIFIC",
    }
    row["attention_decision_set"] = {"suppressed": [{"decision": decision}]}
    silent = assess(row, [0, 0, 10, 10])
    assert silent["first_loss_stage"] == "NONE_SEMANTICS_AUTHORIZED_NO_PRESENTATION"
    assert silent["presentation"] == "NOT_PRESENTED"
    assert silent["attention_reasons"] == ["COOLDOWN"]
