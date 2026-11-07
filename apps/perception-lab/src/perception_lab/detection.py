"""Framework-free detector values in continuous original-camera edge coordinates."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import TYPE_CHECKING

from .contracts import ComponentProvenance, FrameIdentity

if TYPE_CHECKING:
    from .perceived_entity import PerceivedEntityObservation

TAXONOMY_VERSION = "sentinel-coco-p0-v1"


class ObjectClass(StrEnum):
    PERSON = "PERSON"
    BICYCLE = "BICYCLE"
    MOTORCYCLE = "MOTORCYCLE"
    CAR = "CAR"
    BUS = "BUS"
    TRUCK = "TRUCK"
    TRAIN = "TRAIN"
    DOG = "DOG"
    UNKNOWN = "UNKNOWN"


class ObjectGroup(StrEnum):
    PEDESTRIAN = "PEDESTRIAN"
    VEHICLE = "VEHICLE"
    CYCLIST = "CYCLIST"
    ANIMAL = "ANIMAL"
    STATIC_OBJECT = "STATIC_OBJECT"
    UNKNOWN = "UNKNOWN"


# COCO's sparse annotation IDs, deliberately NOT the model's contiguous indices.
COCO_CATEGORIES = {
    1: ObjectClass.PERSON,
    2: ObjectClass.BICYCLE,
    3: ObjectClass.CAR,
    4: ObjectClass.MOTORCYCLE,
    6: ObjectClass.BUS,
    7: ObjectClass.TRAIN,
    8: ObjectClass.TRUCK,
    18: ObjectClass.DOG,
}
P0_CLASSES = frozenset(COCO_CATEGORIES.values())


def semantic_class(model_name: str) -> ObjectClass:
    """Map verified model names, never assume contiguous IDs equal COCO category IDs."""
    return {item.value.lower(): item for item in P0_CLASSES}.get(model_name, ObjectClass.UNKNOWN)


def group(label: ObjectClass) -> ObjectGroup:
    if label == ObjectClass.PERSON:
        return ObjectGroup.PEDESTRIAN
    if label in {ObjectClass.BICYCLE, ObjectClass.MOTORCYCLE}:
        # CYCLIST is reserved for a future fused rider hypothesis, never inferred here.
        return ObjectGroup.VEHICLE
    if label in {ObjectClass.CAR, ObjectClass.BUS, ObjectClass.TRUCK, ObjectClass.TRAIN}:
        return ObjectGroup.VEHICLE
    return ObjectGroup.ANIMAL if label == ObjectClass.DOG else ObjectGroup.UNKNOWN


@dataclass(frozen=True)
class Box:
    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        if not all(isfinite(v) for v in self.coordinates):
            raise ValueError("Box coordinates must be finite")
        if self.x2 < self.x1 or self.y2 < self.y1 or not isfinite(self.area):
            raise ValueError("Invalid box extent")

    @property
    def coordinates(self) -> tuple[float, float, float, float]:
        return self.x1, self.y1, self.x2, self.y2

    @property
    def area(self) -> float:
        return (self.x2 - self.x1) * (self.y2 - self.y1)


@dataclass(frozen=True)
class Detection:
    class_id: int
    class_name: str
    label: ObjectClass
    confidence: float
    box: Box
    # Temporary V0 compatibility carrier; provider concepts never become enum members.
    entity_observation: "PerceivedEntityObservation | None" = None

    def __post_init__(self) -> None:
        if self.class_id < 0 or not self.class_name or not 0 <= self.confidence <= 1:
            raise ValueError("Invalid detection")
        if semantic_class(self.class_name) != self.label:
            raise ValueError("Class name and taxonomy disagree")
        if self.entity_observation is not None and (
            self.entity_observation.bbox != self.box
            or self.entity_observation.region_confidence != self.confidence
            or self.label != ObjectClass.UNKNOWN
        ):
            raise ValueError("Generic compatibility carrier must preserve geometry and confidence")


@dataclass(frozen=True)
class DetectionBatch:
    identity: FrameIdentity
    detections: tuple[Detection, ...]
    provenance: ComponentProvenance
    transform_hash: str
    inference_ns: int
    postprocess_ns: int
    taxonomy_version: str = TAXONOMY_VERSION

    def __post_init__(self) -> None:
        if self.taxonomy_version != TAXONOMY_VERSION:
            raise ValueError("Unsupported detection taxonomy")
        if len(self.transform_hash) != 64 or any(
            c not in "0123456789abcdef" for c in self.transform_hash
        ):
            raise ValueError("Expected transform SHA256")
        if self.inference_ns < 0 or self.postprocess_ns < 0:
            raise ValueError("Negative duration")

    @property
    def boxes(self) -> tuple[tuple[float, float, float, float], ...]:
        return tuple(d.box.coordinates for d in self.detections)
