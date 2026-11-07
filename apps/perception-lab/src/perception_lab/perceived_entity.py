"""V0.2 immutable model-independent observations; no provider class indices."""

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Literal

from .contracts import FrameIdentity
from .detection import Box


class SemanticGroup(StrEnum):
    PERSON = "PERSON"
    VEHICLE = "VEHICLE"
    TWO_WHEELER = "TWO_WHEELER"
    ANIMAL = "ANIMAL"
    MOBILITY_AID = "MOBILITY_AID"
    GROUND_OBSTACLE = "GROUND_OBSTACLE"
    STRUCTURE = "STRUCTURE"
    FURNITURE = "FURNITURE"
    ROAD_INFRASTRUCTURE = "ROAD_INFRASTRUCTURE"
    VEGETATION = "VEGETATION"
    UNKNOWN = "UNKNOWN"


def identifier(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}", value):
        raise ValueError("Invalid bounded identifier")


def probability(value: float) -> None:
    """Legacy validator name: bounds a unit-interval score, not its calibration."""
    if isinstance(value, bool) or not isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Invalid unit-interval score")


def normalized_concept(label: str) -> str:
    if not isinstance(label, str) or not 1 <= len(label) <= 128:
        raise ValueError("Invalid concept length")
    if any(unicodedata.category(c).startswith("C") for c in label):
        raise ValueError("Control characters are forbidden in concepts")
    normalized = " ".join(unicodedata.normalize("NFKC", label).casefold().split())
    if not normalized or len(normalized) > 128:
        raise ValueError("Invalid normalized concept")
    return normalized


@dataclass(frozen=True)
class SemanticConcept:
    raw_label: str
    normalized_label: str
    confidence: float
    source: str
    vocabulary_id: str
    vocabulary_version: str
    embedding_reference: str | None = None
    score_basis: Literal[
        "DETECTOR_JOINT_SCORE",
        "CLASS_SCORE",
        "OPEN_VOCAB_SIMILARITY",
        "TEACHER_SCORE",
        "TRACK_FUSED_EVIDENCE",
        "UNKNOWN",
    ] = "UNKNOWN"
    calibration_status: Literal["UNCALIBRATED", "CALIBRATED", "UNKNOWN"] = "UNCALIBRATED"

    def __post_init__(self) -> None:
        if normalized_concept(self.raw_label) != self.normalized_label:
            raise ValueError("Concept normalization mismatch")
        probability(self.confidence)
        if self.score_basis not in {
            "DETECTOR_JOINT_SCORE",
            "CLASS_SCORE",
            "OPEN_VOCAB_SIMILARITY",
            "TEACHER_SCORE",
            "TRACK_FUSED_EVIDENCE",
            "UNKNOWN",
        } or self.calibration_status not in {"UNCALIBRATED", "CALIBRATED", "UNKNOWN"}:
            raise ValueError("Invalid semantic score metadata")
        for value in (self.source, self.vocabulary_id, self.vocabulary_version):
            identifier(value)
        if self.embedding_reference is not None:
            identifier(self.embedding_reference)


@dataclass(frozen=True)
class SemanticResolution:
    group: SemanticGroup
    confidence: float
    resolver_version: str
    ontology_version: str
    method: Literal["HIERARCHY", "EMBEDDING", "UNKNOWN"]
    spoken_label: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.group, SemanticGroup) or self.method not in (
            "HIERARCHY",
            "EMBEDDING",
            "UNKNOWN",
        ):
            raise ValueError("Invalid semantic resolution")
        probability(self.confidence)
        identifier(self.resolver_version)
        identifier(self.ontology_version)
        if self.spoken_label is not None:
            normalized_concept(self.spoken_label)
        if self.group == SemanticGroup.UNKNOWN and (
            self.confidence != 0 or self.method != "UNKNOWN"
        ):
            raise ValueError("Unknown resolution cannot claim semantic confidence")
        if self.group != SemanticGroup.UNKNOWN and self.method == "UNKNOWN":
            raise ValueError("Known resolution requires supporting method")


@dataclass(frozen=True)
class PerceivedEntityObservation:
    observation_id: str
    source_frame: FrameIdentity
    bbox: Box
    region_confidence: float
    objectness_confidence: float | None
    confidence_basis: Literal["OBJECTNESS", "JOINT_DETECTION_SCORE", "REGION_PROPOSAL"]
    concept: SemanticConcept | None
    semantic_resolution: SemanticResolution | None
    physical_status: Literal["PHYSICAL_OBJECT_CANDIDATE", "UNKNOWN_PHYSICAL_OBJECT"]
    orientation_transform_sha256: str
    quality: Literal["GOOD", "DEGRADED", "UNRELIABLE", "UNKNOWN"]
    provider_id: str
    model_version: str
    mask_reference: str | None = None
    schema_version: Literal[1] = 1
    source_validity: Literal["VALIDATED_RUNTIME_OUTPUT", "UNKNOWN"] = "UNKNOWN"
    source_validation_provenance: str | None = None
    provider_configuration_sha256: str | None = None

    def __post_init__(self) -> None:
        for value in (self.observation_id, self.provider_id, self.model_version):
            identifier(value)
        if not isinstance(self.source_frame, FrameIdentity) or not isinstance(self.bbox, Box):
            raise ValueError("Typed frame identity and geometry are required")
        if self.bbox.area <= 0:
            raise ValueError("Physical object candidate requires nonempty region")
        probability(self.region_confidence)
        if self.objectness_confidence is not None:
            probability(self.objectness_confidence)
        if self.confidence_basis not in ("OBJECTNESS", "JOINT_DETECTION_SCORE", "REGION_PROPOSAL"):
            raise ValueError("Unknown confidence basis")
        if (self.confidence_basis == "OBJECTNESS") != (self.objectness_confidence is not None):
            raise ValueError("Do not relabel joint detector confidence as independent objectness")
        if self.concept is not None and not isinstance(self.concept, SemanticConcept):
            raise ValueError("Invalid concept")
        if self.semantic_resolution is not None and not isinstance(
            self.semantic_resolution, SemanticResolution
        ):
            raise ValueError("Invalid semantic resolution")
        if (
            self.semantic_resolution
            and self.semantic_resolution.group != SemanticGroup.UNKNOWN
            and self.concept is None
        ):
            raise ValueError("Known semantic group requires a concept")
        if self.physical_status not in ("PHYSICAL_OBJECT_CANDIDATE", "UNKNOWN_PHYSICAL_OBJECT"):
            raise ValueError("Invalid physical candidate status")
        if (
            self.quality not in ("GOOD", "DEGRADED", "UNRELIABLE", "UNKNOWN")
            or self.schema_version != 1
        ):
            raise ValueError("Invalid quality or schema")
        if not re.fullmatch(r"[a-f0-9]{64}", self.orientation_transform_sha256):
            raise ValueError("Transform provenance must be SHA256")
        if self.mask_reference is not None:
            identifier(self.mask_reference)
        if self.source_validity not in {"VALIDATED_RUNTIME_OUTPUT", "UNKNOWN"}:
            raise ValueError("Invalid source validity")
        if self.source_validity == "VALIDATED_RUNTIME_OUTPUT":
            if self.source_validation_provenance is None:
                raise ValueError("Validated source requires explicit provenance")
            identifier(self.source_validation_provenance)
        if self.provider_configuration_sha256 is not None and not re.fullmatch(
            r"[a-f0-9]{64}", self.provider_configuration_sha256
        ):
            raise ValueError("Invalid provider configuration hash")
