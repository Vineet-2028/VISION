from dataclasses import replace
from pathlib import Path

import pytest

from perception_lab.concept_resolver import HierarchyConceptResolver
from perception_lab.contracts import FrameIdentity, TimingProvenance
from perception_lab.detection import Box
from perception_lab.entity_adapter import JointScoreEntityAdapter, ProviderRegion


def adapter(vocabulary):
    return JointScoreEntityAdapter(
        "provider",
        "1",
        "test-vocabulary",
        "1",
        vocabulary,
        HierarchyConceptResolver(
            Path(__file__).resolve().parents[3]
            / "configs/perception/ontology/vision-domain-v1.json"
        ),
    )


def test_arbitrary_labels_survive_without_p0_taxonomy_and_missing_label_keeps_region():
    instance = adapter({100: "bus shelter", 200: "labrador retriever"})
    identity = FrameIdentity("source", 1, 100, TimingProvenance.SYNTHETIC)
    boxes = [Box(i * 20, 0, i * 20 + 10, 10) for i in range(4)]
    observations = instance.convert(
        identity,
        tuple(
            ProviderRegion(box, 0.8, index)
            for box, index in zip(boxes, [100, 200, 999, None], strict=True)
        ),
        "a" * 64,
    )
    assert len(observations) == 4
    assert [item.bbox for item in observations] == boxes
    assert observations[0].concept.raw_label == "bus shelter"
    assert observations[1].concept.raw_label == "labrador retriever"
    assert observations[2].concept is None and observations[3].concept is None
    assert all(item.source_frame == identity for item in observations)
    assert all(item.objectness_confidence is None for item in observations)
    assert all(item.confidence_basis == "JOINT_DETECTION_SCORE" for item in observations)
    assert len({item.observation_id for item in observations}) == 4


def test_adapter_copies_vocabulary_to_prevent_live_relabeling():
    vocabulary = {0: "chair"}
    instance = adapter(vocabulary)
    vocabulary[0] = "bus"
    assert instance.vocabulary[0] == "chair"
    with pytest.raises(TypeError):
        instance.vocabulary[0] = "bus"


def test_observation_ids_do_not_collide_between_sources_or_providers():
    instance = adapter({0: "chair"})
    identity = FrameIdentity("source", 1, 100, TimingProvenance.SYNTHETIC)
    regions = (ProviderRegion(Box(0, 0, 10, 10), 0.8, 0),)
    first = instance.convert(identity, regions, "a" * 64)[0].observation_id
    other_source = instance.convert(replace(identity, source_id="other"), regions, "a" * 64)[
        0
    ].observation_id
    other = JointScoreEntityAdapter(
        "other-provider", "1", "test-vocabulary", "1", {0: "chair"}, instance.resolver
    )
    other_provider = other.convert(identity, regions, "a" * 64)[0].observation_id
    assert len({first, other_source, other_provider}) == 3
    assert first == instance.convert(identity, regions, "a" * 64)[0].observation_id


@pytest.mark.parametrize("vocabulary", [{-1: "chair"}, {False: "chair"}, {0: "bad\nlabel"}])
def test_invalid_vocabulary_is_rejected_at_setup(vocabulary):
    with pytest.raises(ValueError):
        adapter(vocabulary)


@pytest.mark.parametrize("score", [float("nan"), float("inf"), True, -1, 2])
def test_invalid_provider_scores_are_rejected(score):
    with pytest.raises(ValueError):
        ProviderRegion(Box(0, 0, 10, 10), score, 0)
