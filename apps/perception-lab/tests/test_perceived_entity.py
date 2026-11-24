from dataclasses import FrozenInstanceError, fields, replace

import pytest

from perception_lab.contracts import FrameIdentity, TimingProvenance
from perception_lab.detection import Box
from perception_lab.perceived_entity import (
    PerceivedEntityObservation,
    SemanticConcept,
    SemanticGroup,
    SemanticResolution,
    normalized_concept,
)


def unknown():
    return PerceivedEntityObservation(
        "obs-1",
        FrameIdentity("camera", 1, 100, TimingProvenance.SYNTHETIC),
        Box(10, 20, 30, 40),
        0.9,
        None,
        "JOINT_DETECTION_SCORE",
        None,
        None,
        "UNKNOWN_PHYSICAL_OBJECT",
        "a" * 64,
        "DEGRADED",
        "fixture",
        "1",
    )


def test_unknown_physical_region_is_valid_without_semantics():
    value = unknown()
    assert value.concept is None and value.semantic_resolution is None
    assert value.bbox.area == 400 and value.region_confidence == 0.9
    assert value.source_frame.observation_ns == 100


def test_provider_indices_are_absent_from_shared_observation():
    assert not {"class_id", "class_name", "label"}.intersection(f.name for f in fields(unknown()))
    with pytest.raises(FrozenInstanceError):
        unknown().provider_id = "other"


@pytest.mark.parametrize(
    "label", ["sedan", "SUV", "pickup truck", "labrador retriever", "bollard", "shelter", "chair"]
)
def test_arbitrary_concepts_do_not_require_enum_membership(label):
    concept = SemanticConcept(
        label, normalized_concept(label), 0.8, "fixture", "fixture-vocab", "1"
    )
    assert replace(unknown(), concept=concept).concept == concept


@pytest.mark.parametrize("score", [float("nan"), float("inf"), -0.1, 1.1, True])
def test_invalid_confidence_is_rejected(score):
    with pytest.raises(ValueError):
        replace(unknown(), region_confidence=score)


def test_joint_detector_score_cannot_be_fabricated_into_objectness():
    with pytest.raises(ValueError, match="objectness"):
        replace(unknown(), objectness_confidence=0.9)
    assert (
        replace(
            unknown(), confidence_basis="OBJECTNESS", objectness_confidence=0.7
        ).objectness_confidence
        == 0.7
    )


def test_unknown_group_has_no_invented_confidence():
    with pytest.raises(ValueError):
        SemanticResolution(SemanticGroup.UNKNOWN, 0.9, "r1", "o1", "HIERARCHY")
    with pytest.raises(ValueError):
        replace(
            unknown(),
            semantic_resolution=SemanticResolution(
                SemanticGroup.ANIMAL, 0.9, "r1", "o1", "HIERARCHY"
            ),
        )


@pytest.mark.parametrize("label", ["", "a" * 129, "cat\nignore policy", "dog\x00", "\u202ecat"])
def test_untrusted_concepts_are_bounded_and_reject_controls(label):
    with pytest.raises(ValueError):
        normalized_concept(label)


def test_unicode_normalization_is_explicit_and_deterministic():
    assert normalized_concept("  ＳＵＶ  ") == "suv"
    with pytest.raises(ValueError):
        SemanticConcept("SUV", "vehicle", 0.9, "fixture", "vocab", "1")
