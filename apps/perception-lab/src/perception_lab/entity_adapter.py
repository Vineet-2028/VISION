"""Provider boundary: preserve arbitrary vocabulary concepts without domain enums.

Provider indices terminate here. Boxes must already be inverse-mapped into original
camera edge coordinates using the supplied transform; no pixel/physical guess is made.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .concept_resolver import ConceptResolver
from .config import canonical_hash
from .contracts import FrameIdentity
from .detection import Box
from .perceived_entity import (
    PerceivedEntityObservation,
    SemanticConcept,
    identifier,
    normalized_concept,
    probability,
)


@dataclass(frozen=True)
class ProviderRegion:
    bbox: Box
    joint_score: float
    vocabulary_index: int | None

    def __post_init__(self) -> None:
        probability(self.joint_score)
        if self.vocabulary_index is not None and (
            type(self.vocabulary_index) is not int or self.vocabulary_index < 0
        ):
            raise ValueError("Invalid provider vocabulary index")


class JointScoreEntityAdapter:
    """Closed/open-vocabulary joint scores are never independent objectness scores."""

    def __init__(
        self,
        provider_id: str,
        model_version: str,
        vocabulary_id: str,
        vocabulary_version: str,
        vocabulary: Mapping[int, str],
        resolver: ConceptResolver,
    ) -> None:
        for value in (provider_id, model_version, vocabulary_id, vocabulary_version):
            identifier(value)
        if len(vocabulary) > 10000:
            raise ValueError("Vocabulary exceeds adapter bound")
        for index, label in vocabulary.items():
            if type(index) is not int or index < 0:
                raise ValueError("Invalid vocabulary index")
            normalized_concept(label)
        self.provider_id, self.model_version = provider_id, model_version
        self.vocabulary_id, self.vocabulary_version = vocabulary_id, vocabulary_version
        self.vocabulary = MappingProxyType(dict(vocabulary))
        self.resolver = resolver

    def convert(
        self,
        identity: FrameIdentity,
        regions: tuple[ProviderRegion, ...],
        transform_sha256: str,
    ) -> tuple[PerceivedEntityObservation, ...]:
        if len(regions) > 10000:
            raise ValueError("Region count exceeds adapter bound")
        observations = []
        for index, region in enumerate(regions):
            raw_label = (
                self.vocabulary.get(region.vocabulary_index)
                if region.vocabulary_index is not None
                else None
            )
            concept = (
                SemanticConcept(
                    raw_label,
                    normalized_concept(raw_label),
                    region.joint_score,
                    self.provider_id,
                    self.vocabulary_id,
                    self.vocabulary_version,
                )
                if raw_label is not None
                else None
            )
            observations.append(
                PerceivedEntityObservation(
                    "region-"
                    + canonical_hash(
                        {
                            "source_id": identity.source_id,
                            "sequence": identity.sequence,
                            "observation_ns": identity.observation_ns,
                            "timing": identity.timing.value,
                            "provider": self.provider_id,
                            "model": self.model_version,
                            "index": index,
                            "bbox": region.bbox.coordinates,
                            "transform": transform_sha256,
                        }
                    ),
                    identity,
                    region.bbox,
                    region.joint_score,
                    None,
                    "JOINT_DETECTION_SCORE",
                    concept,
                    self.resolver.resolve(concept) if concept else None,
                    "PHYSICAL_OBJECT_CANDIDATE" if concept else "UNKNOWN_PHYSICAL_OBJECT",
                    transform_sha256,
                    "UNKNOWN",
                    self.provider_id,
                    self.model_version,
                )
            )
        return tuple(observations)
