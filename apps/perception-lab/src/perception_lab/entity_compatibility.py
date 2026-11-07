"""Temporary adapter for legacy pipeline containers, never a semantic taxonomy."""

from .contracts import ComponentProvenance, FrameIdentity
from .detection import Detection, DetectionBatch, ObjectClass
from .perceived_entity import PerceivedEntityObservation


def legacy_batch(
    identity: FrameIdentity,
    observations: tuple[PerceivedEntityObservation, ...],
    provenance: ComponentProvenance,
    transform_hash: str,
    inference_ns: int = 0,
    postprocess_ns: int = 0,
) -> DetectionBatch:
    if len(observations) > 10000:
        raise ValueError("Generic batch exceeds defensive bound")
    if any(
        o.source_frame != identity or o.orientation_transform_sha256 != transform_hash
        for o in observations
    ):
        raise ValueError("Generic batch frame/transform mismatch")
    if len({o.observation_id for o in observations}) != len(observations):
        raise ValueError("Duplicate generic observation identity")
    return DetectionBatch(
        identity,
        tuple(
            Detection(0, "unknown", ObjectClass.UNKNOWN, o.region_confidence, o.bbox, o)
            for o in observations
        ),
        provenance,
        transform_hash,
        inference_ns,
        postprocess_ns,
    )
