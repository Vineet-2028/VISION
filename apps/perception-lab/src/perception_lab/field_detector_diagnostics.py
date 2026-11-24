"""Opt-in observation of the unchanged PicoDet vendor output boundary."""

from typing import Any

import numpy as np

from .contracts import FrameIdentity
from .detection import Box, DetectionBatch
from .edge_runtime import PicoDetDetector
from .preprocessing import PreparedImage


def summarize_vendor_output(data: Any, threshold: float) -> dict[str, object]:
    if data.ndim != 2 or data.shape[1] != 6 or not np.isfinite(data).all():
        return {"status": "INVALID_VENDOR_OUTPUT"}
    rows = data[data[:, 0] != -1]
    if np.any(rows[:, 0] != np.floor(rows[:, 0])) or np.any(
        (rows[:, 0] < 0) | (rows[:, 0] >= 80) | (rows[:, 1] < 0) | (rows[:, 1] > 1)
    ):
        return {"status": "INVALID_VENDOR_OUTPUT"}
    rejected = rows[rows[:, 1] < threshold]
    return {
        "schema": "vision.picodet.boundary.v1",
        "status": "OBSERVED_POST_VENDOR_NMS",
        "raw_pre_nms_count": None,
        "vendor_score_rejected_count": None,
        "nms_rejected_count": None,
        "embedded_score_floor": 0.025,
        "adapter_threshold": threshold,
        "vendor_output_count": len(rows),
        "adapter_score_rejected_count": len(rejected),
        "adapter_score_survivor_count": len(rows) - len(rejected),
        "score_basis": "DETECTOR_JOINT_SCORE_UNCALIBRATED",
        "rejected_sample_limit": 16,
        "rejected_samples_truncated": len(rejected) > 16,
        "rejected_samples": [
            {
                "vendor_class_id": int(row[0]),
                "score": float(row[1]),
                "model_pixel_box": [float(v) for v in row[2:]],
                "coordinate_domain": "MODEL_416_PIXELS",
                "reason": "BELOW_DETECTION_THRESHOLD",
            }
            for row in rejected[:16]
        ],
    }


class ObservedSession:
    def __init__(self, session: Any, owner: Any) -> None:
        self.session = session
        self.owner = owner

    def get_inputs(self) -> Any:
        return self.session.get_inputs()

    def run(self, outputs: Any, inputs: Any) -> Any:
        result = self.session.run(outputs, inputs)
        self.owner.diagnostic = summarize_vendor_output(result[0], self.owner.confidence)
        return result


class DiagnosticPicoDet(PicoDetDetector):
    """Uses the exact baseline inference and filtering, with one bounded snapshot."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.diagnostic: dict[str, object] = {}
        self.session = ObservedSession(self.session, self)

    def detect(self, image: PreparedImage, identity: FrameIdentity) -> DetectionBatch:
        self.diagnostic = {}
        result = super().detect(image, identity)
        mapping = image.mapping.resized_padded(416, 416, (416, 416))
        samples = self.diagnostic.get("rejected_samples")
        if isinstance(samples, list):
            for sample in samples:
                try:
                    sample["original_box"] = list(
                        mapping.restore_box(Box(*sample["model_pixel_box"])).coordinates
                    )
                except ValueError:
                    sample["original_box"] = None
                    sample["mapping_status"] = "INVALID_BOX"
        self.diagnostic.update(
            source_sequence=identity.sequence,
            source_observation_ns=str(identity.observation_ns),
            source_id=identity.source_id,
            model_sha256=self.provenance.model_version,
            configuration_hash=self.provenance.configuration_hash,
            transform_hash=result.transform_hash,
            final_detection_count=len(result.detections),
            accepted_samples=[
                {
                    "original_box": list(d.box.coordinates),
                    "class_name": d.class_name,
                    "score": d.confidence,
                }
                for d in result.detections[:32]
            ],
            accepted_samples_truncated=len(result.detections) > 32,
        )
        return result
