"""Explicit opt-in boundary from validated PicoDet output to generic observations."""

from dataclasses import replace

from .concept_resolver import ConceptResolver
from .detection import DetectionBatch, ObjectClass
from .entity_adapter import JointScoreEntityAdapter, ProviderRegion


class PicoDetSemanticAdapter:
    """Valid runtime output is distinct from calibrated semantic confidence.

    This accepts only the pinned runtime's provenance. Track association and
    temporal agreement are validated downstream, never asserted by this boundary.
    """

    def __init__(self, resolver: ConceptResolver, model_sha256: str) -> None:
        from .edge_runtime import P0_NAMES, PINS

        if model_sha256 != PINS["picodet-s"]:
            raise ValueError("PicoDet semantic boundary requires pinned model")
        self.model_sha256 = model_sha256
        self.adapter = JointScoreEntityAdapter(
            "picodet-s", model_sha256, "coco-p0-runtime", "1", P0_NAMES, resolver
        )

    def convert(self, batch: DetectionBatch) -> DetectionBatch:
        if (
            batch.provenance.model_id != "picodet-s"
            or batch.provenance.model_version != self.model_sha256
        ):
            raise ValueError("PicoDet runtime provenance mismatch")
        observations = self.adapter.convert(
            batch.identity,
            tuple(ProviderRegion(d.box, d.confidence, d.class_id) for d in batch.detections),
            batch.transform_hash,
        )
        return replace(
            batch,
            detections=tuple(
                replace(
                    detection,
                    class_id=0,
                    class_name="unknown",
                    label=ObjectClass.UNKNOWN,
                    entity_observation=replace(
                        observation,
                        concept=replace(observation.concept, score_basis="DETECTOR_JOINT_SCORE")
                        if observation.concept
                        else None,
                        source_validity="VALIDATED_RUNTIME_OUTPUT",
                        source_validation_provenance="picodet-pinned-finite-output-inverse-map-v1",
                        provider_configuration_sha256=batch.provenance.configuration_hash,
                    ),
                )
                for detection, observation in zip(batch.detections, observations, strict=True)
            ),
        )
