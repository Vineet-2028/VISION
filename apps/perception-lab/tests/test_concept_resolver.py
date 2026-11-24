import json
from pathlib import Path

import pytest

from perception_lab.concept_resolver import HierarchyConceptResolver
from perception_lab.perceived_entity import SemanticConcept, SemanticGroup, normalized_concept

ONTOLOGY = Path(__file__).resolve().parents[3] / "configs/perception/ontology/vision-domain-v1.json"


def concept(label):
    return SemanticConcept(label, normalized_concept(label), 0.8, "fixture", "vocab", "1")


def test_unknown_concept_remains_unknown_instead_of_guessing():
    resolver = HierarchyConceptResolver(ONTOLOGY)
    assert resolver.resolve(concept("sedan")).group == SemanticGroup.UNKNOWN
    assert resolver.resolve(concept("animal")).group == SemanticGroup.ANIMAL


def test_versioned_hierarchy_resolves_without_source_label_branches(tmp_path):
    data = json.loads(ONTOLOGY.read_text())
    data["hierarchy"] = {
        "sedan": "passenger vehicle",
        "passenger vehicle": "vehicle",
        "labrador retriever": "dog",
        "dog": "animal",
    }
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(data))
    resolver = HierarchyConceptResolver(path)
    assert resolver.resolve(concept("SEDAN")).group == SemanticGroup.VEHICLE
    assert resolver.resolve(concept("labrador retriever")).group == SemanticGroup.ANIMAL
    assert resolver.resolve(concept("unseen object")).confidence == 0


@pytest.mark.parametrize(
    "hierarchy", [{"a": "b", "b": "a"}, {"a": "missing"}, {"animal": "vehicle"}]
)
def test_invalid_hierarchies_fail_before_runtime(tmp_path, hierarchy):
    data = json.loads(ONTOLOGY.read_text())
    data["hierarchy"] = hierarchy
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        HierarchyConceptResolver(path)


def test_duplicate_keys_and_oversized_data_rejected(tmp_path):
    path = tmp_path / "fixture.json"
    for payload in ['{"schema_version":1,"schema_version":1}', " " * 262_145]:
        path.write_text(payload)
        with pytest.raises(ValueError):
            HierarchyConceptResolver(path)
