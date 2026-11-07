"""Data-only bounded hierarchy resolution. Never invokes a model or network."""

import hashlib
import json
from pathlib import Path
from typing import Protocol

from .perceived_entity import (
    SemanticConcept,
    SemanticGroup,
    SemanticResolution,
    identifier,
    normalized_concept,
)


class ConceptResolver(Protocol):
    def resolve(self, concept: SemanticConcept) -> SemanticResolution: ...


class HierarchyConceptResolver:
    def __init__(self, path: Path) -> None:
        with path.open("rb") as stream:
            payload = stream.read(262_145)
        if len(payload) > 262_144:
            raise ValueError("Ontology byte limit exceeded")

        def unique(items: list[tuple[str, object]]) -> dict[str, object]:
            result: dict[str, object] = {}
            for key, value in items:
                if key in result:
                    raise ValueError("Duplicate ontology key")
                result[key] = value
            return result

        data = json.loads(payload, object_pairs_hook=unique)
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise ValueError("Unsupported ontology")
        version = data.get("version")
        if not isinstance(version, str):
            raise ValueError("Ontology version must be text")
        identifier(version)
        self.version: str = version
        self.sha256 = hashlib.sha256(payload).hexdigest()
        groups = data.get("groups")
        hierarchy = data.get("hierarchy")
        if not isinstance(groups, list) or len(groups) != len(SemanticGroup):
            raise ValueError("Ontology must define every domain group exactly once")
        if not isinstance(hierarchy, dict) or len(hierarchy) > 4096:
            raise ValueError("Invalid bounded hierarchy")
        self.anchors: dict[str, SemanticGroup] = {}
        self.spoken_labels: dict[SemanticGroup, str] = {}
        seen: set[SemanticGroup] = set()
        for row in groups:
            if not isinstance(row, dict):
                raise ValueError("Invalid group")
            group_id = row.get("id")
            if not isinstance(group_id, str):
                raise ValueError("Group identifier must be text")
            group = SemanticGroup(group_id)
            if group in seen:
                raise ValueError("Duplicate group")
            seen.add(group)
            spoken = row.get("spoken_label", "Object")
            if not isinstance(spoken, str):
                raise ValueError("Group spoken label must be text")
            normalized_concept(spoken)
            self.spoken_labels[group] = spoken
            anchors = row.get("anchors")
            if not isinstance(anchors, list) or len(anchors) > 64:
                raise ValueError("Invalid group anchors")
            if group == SemanticGroup.UNKNOWN and anchors:
                raise ValueError("Unknown cannot resolve a concept")
            for anchor in anchors:
                key = normalized_concept(anchor)
                if key in self.anchors:
                    raise ValueError("Ambiguous anchor")
                self.anchors[key] = group
        self.parents: dict[str, str] = {}
        for child, parent in hierarchy.items():
            key = normalized_concept(child)
            if key in self.parents or key in self.anchors:
                raise ValueError("Ambiguous hierarchy node")
            self.parents[key] = normalized_concept(parent)
        # Precompute once. Traversal and cycle checks never enter the per-frame path.
        self.resolved = dict(self.anchors)
        for key in self.parents:
            cursor = key
            visited: set[str] = set()
            while cursor in self.parents:
                if cursor in visited or len(visited) >= 32:
                    raise ValueError("Cyclic or excessive hierarchy depth")
                visited.add(cursor)
                cursor = self.parents[cursor]
            if cursor not in self.anchors:
                raise ValueError("Hierarchy must end at a declared domain anchor")
            self.resolved[key] = self.anchors[cursor]

    def resolve(self, concept: SemanticConcept) -> SemanticResolution:
        group = self.resolved.get(concept.normalized_label, SemanticGroup.UNKNOWN)
        return SemanticResolution(
            group,
            0 if group == SemanticGroup.UNKNOWN else concept.confidence,
            "hierarchy-v1",
            self.version,
            "UNKNOWN" if group == SemanticGroup.UNKNOWN else "HIERARCHY",
            self.spoken_labels[group] if group != SemanticGroup.UNKNOWN else None,
        )
