"""Exact upstream identity and delayed output retain one immutable causal record."""

from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

import pytest
from test_alerts import batch
from test_corridor import scene
from test_picodet_semantics import observation
from test_world_model import identity

from perception_lab.alerts import AlertEngine
from perception_lab.event_lineage import attach_event_lineage


def update(geometry):
    world = scene(geometry)
    entity = replace(
        world.entities[0], entity_observation=replace(observation(0), source_frame=identity())
    )
    world = replace(world, entities=(entity,))
    decisions = batch()
    decisions = replace(
        decisions,
        session_id=world.session_id,
        selected=(replace(decisions.selected[0], entity_id=entity.entity_id),),
    )
    interaction = SimpleNamespace(entity_id=entity.entity_id, state_timestamp=0, trajectory_id="t1")
    risk = SimpleNamespace(entity_id=entity.entity_id, state_timestamp=0)
    return SimpleNamespace(
        identity=identity(),
        world_state=world,
        attention_decision_set=decisions,
        interaction_analysis=SimpleNamespace(
            session_id=world.session_id, entity_interactions=(interaction,)
        ),
        risk_assessment_set=SimpleNamespace(session_id=world.session_id, assessments=(risk,)),
    )


def test_lineage_preserved_through_intent_and_presentation(geometry):
    result = update(geometry)
    decisions = attach_event_lineage(result)
    lineage = decisions.selected[0].lineage
    assert lineage.missing_links == ()
    assert lineage.observation_id == observation(0).observation_id
    assert lineage.track_generation == lineage.track_id.serial
    assert lineage.interaction_record_id.endswith(":interaction:0:t1")
    output = AlertEngine().process(decisions, now_ns=100_000_000).outputs[0]
    assert output.delivered
    assert output.intent.lineage is output.presentation.lineage is lineage
    assert output.intent.alert_id == output.presentation.alert_id
    with pytest.raises(FrozenInstanceError):
        lineage.track_generation = 99
    with pytest.raises(ValueError, match="lineage mismatch"):
        replace(output.intent, event_id="other-event")


def test_missing_interaction_is_explicit_not_an_invented_event(geometry):
    result = update(geometry)
    result.interaction_analysis = None
    lineage = attach_event_lineage(result).selected[0].lineage
    assert lineage.interaction_record_id is None
    assert lineage.missing_links == ("INTERACTION_RECORD_UNAVAILABLE",)


def test_duplicate_and_wrong_session_upstream_are_rejected(geometry):
    result = update(geometry)
    result.risk_assessment_set.assessments *= 2
    with pytest.raises(ValueError, match="duplicate"):
        attach_event_lineage(result)
    result = update(geometry)
    result.interaction_analysis.session_id = "other-session"
    with pytest.raises(ValueError, match="session"):
        attach_event_lineage(result)


def test_track_generation_and_observation_identity_cannot_be_partially_replaced(geometry):
    lineage = attach_event_lineage(update(geometry)).selected[0].lineage
    with pytest.raises(ValueError, match="generation"):
        replace(lineage, track_generation=lineage.track_generation + 1)
    with pytest.raises(ValueError, match="observation identity"):
        replace(lineage, origin_source_identity=None)


def test_lineage_rejects_other_source_and_future_upstream(geometry):
    result = update(geometry)
    result.identity = replace(result.identity, source_id="other-source")
    with pytest.raises(ValueError, match="source/time"):
        attach_event_lineage(result)
    result = update(geometry)
    result.risk_assessment_set.assessments[0].state_timestamp = 1
    with pytest.raises(ValueError, match="future"):
        attach_event_lineage(result)
