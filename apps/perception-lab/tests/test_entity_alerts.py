"""Generic semantic wording preserves admission, identity and delivery expiry."""

from dataclasses import replace

import pytest
from test_alerts import batch
from test_corridor import scene
from test_track_semantics import evidence, feed, fusion

from perception_lab.alerts import AlertEngine
from perception_lab.entity_attention import attach_entity_semantics
from perception_lab.perceived_entity import SemanticConcept, normalized_concept
from perception_lab.world_types import WorldEntityId


def semantic_batch(label="electric scooter", **changes):
    concept = SemanticConcept(label, normalized_concept(label), 0.9, "fixture", "fixture", "1")
    output = batch(concept=concept)
    decision = output.selected[0]
    evidence = replace(decision.semantic_evidence, **{"quality": "GOOD", **changes})
    return replace(output, selected=(replace(decision, semantic_evidence=evidence),))


@pytest.mark.parametrize("label", ["bollard", "electric scooter", "bus shelter"])
def test_arbitrary_stable_concept_renders_without_enum(label):
    output = AlertEngine().process(semantic_batch(label), now_ns=0).outputs[0]
    assert output.status == "READY"
    assert output.intent.category == "UNKNOWN"
    assert output.presentation.speech_text == label.capitalize() + "."
    assert output.intent.physical_validity == "UNVALIDATED"


@pytest.mark.parametrize(
    "changes",
    [
        {"quality": "DEGRADED"},
        {"quality": "UNAVAILABLE"},
        {"entity_id": WorldEntityId("wrong-session", 1)},
        {"observed_ns": 1},
        {"valid_until_ns": 0},
        {"provenance": ()},
    ],
)
def test_unqualified_concept_preserves_generic_alert(changes):
    output = AlertEngine().process(semantic_batch(**changes), now_ns=0).outputs[0]
    assert output.presentation.speech_text == "Object."


def test_concept_expiry_is_rechecked_at_delivery():
    output = (
        AlertEngine()
        .process(semantic_batch(valid_until_ns=10), now_ns=0, delivery_clock=lambda: 10)
        .outputs[0]
    )
    assert output.status == "DROPPED_EXPIRED"
    assert not output.delivered


@pytest.mark.parametrize("label", ["<script>bad</script>", "a" * 49, "one two three four five"])
def test_unbounded_or_markup_concept_falls_back_without_losing_alert(label):
    output = AlertEngine().process(semantic_batch(label), now_ns=0).outputs[0]
    assert output.status == "READY"
    assert output.presentation.speech_text == "Object."


@pytest.mark.parametrize("quality", ["STABLE", "UNKNOWN", "UNSTABLE", "EXPIRED"])
def test_world_semantics_changes_only_evidence(geometry, quality):
    world = scene(geometry)
    entity = world.entities[0]
    semantic_state = feed(fusion(), [evidence(i) for i in range(3)])
    now = 200_000_000
    entity = replace(
        entity,
        track_semantics=replace(semantic_state, track_id=entity.source_track_id, quality=quality),
    )
    world = replace(world, state_timestamp=now, entities=(entity,))
    decisions = batch(now)
    original = replace(decisions.selected[0], entity_id=entity.entity_id)
    decisions = replace(decisions, session_id=world.session_id, selected=(original,))
    result = attach_entity_semantics(decisions, world)
    updated = result.selected[0]
    assert (
        replace(updated, semantic_evidence=None, semantic_authorization_reason="NOT_EVALUATED")
        == original
    )
    assert updated.semantic_authorization_reason == (
        "AUTHORIZED_STABLE_SPECIFIC"
        if quality == "STABLE"
        else "SEMANTIC_EXPIRED"
        if quality == "EXPIRED"
        else "SEMANTIC_UNSTABLE"
    )
    if quality == "STABLE":
        assert updated.semantic_evidence.concept.raw_label == "bollard"
        assert updated.semantic_evidence.entity_id == entity.entity_id
        assert updated.semantic_evidence.valid_until_ns == semantic_state.valid_until_ns
    else:
        assert updated.semantic_evidence is None


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("missing", "NO_TRACK_SEMANTIC_EVIDENCE"),
        ("replaced", "TRACK_REPLACED"),
        ("expired", "SEMANTIC_EXPIRED"),
        ("future", "SEMANTIC_FROM_FUTURE"),
        ("no_time", "SEMANTIC_TIME_UNAVAILABLE"),
    ],
)
def test_semantic_authorization_records_exact_rejection_without_changing_decision(
    geometry, change, reason
):
    world = scene(geometry)
    entity = world.entities[0]
    now = 200_000_000
    semantics = replace(
        feed(fusion(), [evidence(i) for i in range(3)]), track_id=entity.source_track_id
    )
    if change == "missing":
        semantics = None
    elif change == "replaced":
        semantics = replace(semantics, track_id=replace(entity.source_track_id, serial=999))
    elif change == "expired":
        semantics = replace(semantics, valid_until_ns=now)
    elif change == "future":
        semantics = replace(semantics, last_observed_ns=now + 1)
    else:
        semantics = replace(semantics, last_observed_ns=None)
    world = replace(
        world, state_timestamp=now, entities=(replace(entity, track_semantics=semantics),)
    )
    decisions = batch(now)
    original = replace(decisions.selected[0], entity_id=entity.entity_id)
    decisions = replace(decisions, session_id=world.session_id, selected=(original,))
    updated = attach_entity_semantics(decisions, world).selected[0]
    assert updated.semantic_authorization_reason == reason
    assert updated.semantic_evidence is None
    assert replace(updated, semantic_authorization_reason="NOT_EVALUATED") == original
