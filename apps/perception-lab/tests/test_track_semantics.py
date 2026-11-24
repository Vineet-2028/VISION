from dataclasses import FrozenInstanceError, replace

import pytest

from perception_lab.contracts import FrameIdentity, TimingProvenance
from perception_lab.detection import Box
from perception_lab.perceived_entity import (
    PerceivedEntityObservation,
    SemanticConcept,
    normalized_concept,
)
from perception_lab.track_semantics import SemanticFusionConfig, TrackSemanticFusion
from perception_lab.tracking_types import TrackId


def evidence(i, label="bollard", confidence=0.9, quality="GOOD", provider="detector"):
    identity = FrameIdentity("source", i, i * 100_000_000, TimingProvenance.SYNTHETIC)
    concept = (
        None
        if label is None
        else SemanticConcept(label, normalized_concept(label), confidence, provider, "vocab", "1")
    )
    return PerceivedEntityObservation(
        f"obs-{i}",
        identity,
        Box(0, 0, 10, 10),
        confidence,
        None,
        "JOINT_DETECTION_SCORE",
        concept,
        None,
        "UNKNOWN_PHYSICAL_OBJECT",
        "a" * 64,
        quality,
        provider,
        "1",
    )


def fusion(**kwargs):
    return TrackSemanticFusion(
        TrackId("session", 1), evidence(0).source_frame, SemanticFusionConfig(**kwargs)
    )


def feed(state, observations):
    result = None
    for observation in observations:
        now = observation.source_frame.observation_ns
        state.observe(observation, now)
        result = state.snapshot(now)
    return result


def test_stable_name_survives_one_low_quality_conflicting_frame():
    state = fusion()
    first = feed(state, [evidence(i) for i in range(3)])
    assert first.quality == "STABLE" and first.selected_concept.raw_label == "bollard"
    second = feed(state, [evidence(3, "electric scooter", 0.1, "DEGRADED", "teacher")])
    assert second.selected_concept.raw_label == "bollard"
    assert "electric scooter" in second.disagreement
    assert second.providers == ("detector", "teacher")
    assert second.last_observed_ns == 200_000_000


def test_low_confidence_same_label_cannot_refresh_expiry_or_replace_confidence():
    state = fusion()
    feed(state, [evidence(i) for i in range(3)])
    result = feed(state, [evidence(3, confidence=0.1)])
    assert result.selected_concept.confidence == 0.9
    assert result.valid_until_ns == 2_200_000_000
    expired = state.snapshot(2_200_000_000)
    assert expired.selected_concept is None


def test_expiry_is_not_refreshed_by_snapshot_or_unknown_observations():
    state = fusion()
    feed(state, [evidence(i) for i in range(3)])
    result = feed(state, [evidence(3, None)])
    assert result.selected_concept.raw_label == "bollard"
    assert result.last_observed_ns == 200_000_000
    expired = state.snapshot(2_400_000_000)
    assert expired.quality == "EXPIRED" and expired.selected_concept is None
    assert expired.evidence == ()


def test_unknown_first_class_and_immutable_state():
    state = fusion()
    result = feed(state, [evidence(0, None)])
    assert result.quality == "UNKNOWN" and result.selected_concept is None
    with pytest.raises(FrozenInstanceError):
        result.quality = "STABLE"


def test_evidence_and_provider_storage_are_bounded():
    state = fusion(evidence_capacity=4, provider_capacity=1)
    result = feed(state, [evidence(i) for i in range(100)])
    assert len(result.evidence) == 4
    with pytest.raises(ValueError, match="capacity"):
        state.observe(evidence(100, provider="other"), 10_000_000_000)


def test_duplicate_regressing_future_and_other_source_evidence_rejected():
    state = fusion()
    feed(state, [evidence(0)])
    with pytest.raises(ValueError, match="Duplicate"):
        state.observe(evidence(0), 0)
    with pytest.raises(ValueError, match="freshness"):
        state.observe(evidence(2), 0)
    other = replace(evidence(1), source_frame=replace(evidence(1).source_frame, source_id="other"))
    with pytest.raises(ValueError, match="source"):
        state.observe(other, 100_000_000)


def test_new_track_cannot_inherit_previous_track_evidence():
    state = TrackSemanticFusion(
        TrackId("session", 2), evidence(5).source_frame, SemanticFusionConfig()
    )
    with pytest.raises(ValueError, match="birth"):
        state.observe(evidence(2), 500_000_000)
    assert state.snapshot(500_000_000).selected_concept is None


def test_repeated_provider_agreement_on_one_frame_does_not_fake_temporal_support():
    state = fusion()
    result = feed(state, [evidence(0, provider=name) for name in ("a", "b", "c")])
    assert result.quality == "UNSTABLE" and result.selected_concept is None


def test_consistent_new_semantics_eventually_replace_old_label():
    state = fusion(evidence_capacity=4)
    feed(state, [evidence(i) for i in range(3)])
    result = feed(state, [evidence(i, "electric scooter") for i in range(3, 8)])
    assert result.quality == "STABLE"
    assert result.selected_concept.raw_label == "electric scooter"
