"""Hash-pinned official YOLOX-Nano and PicoDet-S ONNX adapter boundaries.

Preprocessing follows the corresponding official release demos, not current YOLO defaults.
PicoDet embeds NMS; its runtime timing is explicitly a COMBINED_VENDOR_STAGE.
"""

import importlib
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .clocks import processing_ns
from .config import canonical_hash
from .contracts import ComponentProvenance, FrameIdentity, PixelFormat
from .detection import Box, Detection, DetectionBatch, semantic_class
from .detector_runtime import file_hash
from .offline import enforce_offline
from .preprocessing import PreparedImage

PINS = {
    "yolox-nano": "c789161ed43c8269fcd4e67c67eeeb4e80c622da2eb296a20bc6007bd18a0b7d",
    "picodet-s": "4b717e3f68f170fafd922c3c7978e52b6ad2ab3615d26b407e7d9aba44eb790f",
}
# Full vendor COCO ordering is unnecessary for non-P0 semantics, but IDs remain intact.
P0_NAMES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    6: "train",
    7: "truck",
    16: "dog",
}


def yolox_rows(output: NDArray[np.float32], confidence: float) -> list[tuple[int, float, Box]]:
    """Decode released raw head; class-wise NMS in model coordinates, IoU 0.45."""
    if output.shape != (1, 3549, 85) or not np.isfinite(output).all():
        raise ValueError("Invalid YOLOX output shape/values")
    decoded = output[0].copy()
    start = 0
    for stride in (8, 16, 32):
        side = 416 // stride
        yy, xx = np.mgrid[:side, :side]
        grid = np.stack((xx, yy), axis=-1).reshape(-1, 2)
        end = start + side * side
        decoded[start:end, :2] = (decoded[start:end, :2] + grid) * stride
        decoded[start:end, 2:4] = np.exp(decoded[start:end, 2:4]) * stride
        start = end
    scores = decoded[:, 4:5] * decoded[:, 5:]
    if not np.isfinite(decoded).all() or np.any(scores < 0) or np.any(scores > 1):
        raise ValueError("Invalid decoded detector values")
    boxes = np.concatenate(
        (decoded[:, :2] - decoded[:, 2:4] / 2, decoded[:, :2] + decoded[:, 2:4] / 2), axis=1
    )
    rows = []
    for category in range(80):
        indices = np.flatnonzero(scores[:, category] >= confidence)
        indices = indices[np.argsort(-scores[indices, category], kind="stable")]
        while indices.size:
            chosen = int(indices[0])
            rows.append(
                (category, float(scores[chosen, category]), Box(*map(float, boxes[chosen])))
            )
            rest = indices[1:]
            # Match released demo's inclusive-pixel NMS convention only within this vendor stage.
            overlap = np.maximum(
                0,
                np.minimum(boxes[chosen, 2:], boxes[rest, 2:])
                - np.maximum(boxes[chosen, :2], boxes[rest, :2])
                + 1,
            )
            intersection = overlap.prod(axis=1)
            areas = (boxes[:, 2:] - boxes[:, :2] + 1).prod(axis=1)
            indices = rest[intersection / (areas[chosen] + areas[rest] - intersection) <= 0.45]
    return sorted(rows, key=lambda row: -row[1])[:300]


class EdgeOnnxDetector:
    model_id = ""

    def __init__(
        self,
        weights: Path,
        sha256: str,
        *,
        size: int = 416,
        confidence: float = 0.05,
        device: str = "cpu",
        half: bool = False,
        threads: int = 1,
    ) -> None:
        if sha256 != PINS[self.model_id] or file_hash(weights) != sha256:
            raise ValueError("Unreviewed checkpoint or hash mismatch")
        if (
            size != 416
            or device != "cpu"
            or half
            or not 1 <= threads <= 16
            or not 0.01 <= confidence <= 1
        ):
            raise ValueError("Released edge models require 416 CPU FP32 and confidence >= .01")
        if self.model_id == "picodet-s" and confidence < 0.025:
            raise ValueError(
                "PicoDet release embeds a .025 score floor; lower thresholds unavailable"
            )
        enforce_offline()
        ort: Any = importlib.import_module("onnxruntime")
        self.cv: Any = importlib.import_module("cv2")
        self.cv.setNumThreads(threads)
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.log_severity_level = 3
        self.session: Any = ort.InferenceSession(
            str(weights.resolve()), options, providers=["CPUExecutionProvider"]
        )
        self.confidence = confidence
        self.last_timings_ns: dict[str, int] = {}
        self.runtime_metadata: dict[str, object] = {
            "providers": self.session.get_providers(),
            "onnxruntime": ort.__version__,
            "nms_mode": "EMBEDDED_COMBINED_VENDOR_STAGE"
            if self.model_id == "picodet-s"
            else "CLASS_WISE_IOU_0.45",
            "native_parity": "NOT_VERIFIED",
            "threads": threads,
            "embedded_score_floor": 0.025 if self.model_id == "picodet-s" else None,
            "inference_stage": "COMBINED_VENDOR_STAGE"
            if self.model_id == "picodet-s"
            else "RUNTIME_INVOCATION",
        }
        self.provenance = ComponentProvenance(
            type(self).__name__,
            "detector",
            self.model_id,
            sha256,
            "onnxruntime-" + ort.__version__ + "/cpu/fp32",
            canonical_hash(
                {
                    "size": size,
                    "confidence": confidence,
                    "threads": threads,
                    "policy": "official-artifact-bgr-v2",
                }
            ),
        )

    def detect(self, image: PreparedImage, identity: FrameIdentity) -> DetectionBatch:
        if image.descriptor.pixel_format != PixelFormat.RGB or image.descriptor.layout != "NHWC":
            raise ValueError("Detector requires RGB NHWC")
        started = processing_ns()
        height, width = image.pixels.shape[:2]
        pixels: NDArray[np.float32]
        if self.model_id == "yolox-nano":
            ratio = min(416 / width, 416 / height)
            dimensions = (max(1, int(width * ratio)), max(1, int(height * ratio)))
            resized = self.cv.resize(image.pixels, dimensions, interpolation=self.cv.INTER_LINEAR)
            pixels = np.full((416, 416, 3), 114, dtype=np.float32)
            pixels[: dimensions[1], : dimensions[0]] = resized
            pixels = np.ascontiguousarray(pixels[:, :, ::-1])  # Released artifact uses raw BGR.
        else:
            dimensions = (416, 416)
            pixels = self.cv.resize(
                image.pixels, dimensions, interpolation=self.cv.INTER_LINEAR
            ).astype(np.float32)
            # Matches the published RGB demo and its reversed mean/std order exactly.
            pixels = (
                (pixels - np.array([103.53, 116.28, 123.675], dtype=np.float32))
                / np.array([57.375, 57.12, 58.395], dtype=np.float32)
            ).astype(np.float32)
        mapping = image.mapping.resized_padded(416, 416, dimensions)
        tensor = np.ascontiguousarray(pixels.transpose(2, 0, 1)[None], dtype=np.float32)
        inputs = {self.session.get_inputs()[0].name: tensor}
        if self.model_id == "picodet-s":
            # Keep outputs in model pixels; Java owns the actual inverse scaling.
            inputs["scale_factor"] = np.ones((1, 2), dtype=np.float32)
        prepared = processing_ns()
        outputs = self.session.run(None, inputs)
        inferred = processing_ns()
        if self.model_id == "yolox-nano":
            rows = yolox_rows(outputs[0], self.confidence)
        else:
            data = outputs[0]
            if data.ndim != 2 or data.shape[1] != 6 or not np.isfinite(data).all():
                raise ValueError("Invalid PicoDet output")
            rows = []
            for category, score, x1, y1, x2, y2 in data:
                if category == -1:  # Vendor no-detection sentinel.
                    continue
                if category != int(category) or not 0 <= category < 80 or not 0 <= score <= 1:
                    raise ValueError("Invalid PicoDet class/confidence")
                if score >= self.confidence:
                    rows.append(
                        (
                            int(category),
                            float(score),
                            Box(float(x1), float(y1), float(x2), float(y2)),
                        )
                    )
        filtered = processing_ns()
        detections = tuple(
            Detection(
                category,
                P0_NAMES.get(category, "coco-" + str(category)),
                semantic_class(P0_NAMES.get(category, "unknown")),
                score,
                mapping.restore_box(box),
            )
            for category, score, box in rows
        )
        restored = processing_ns()
        batch = DetectionBatch(
            identity,
            detections,
            self.provenance,
            mapping.fingerprint,
            inferred - prepared,
            restored - inferred,
        )
        completed = processing_ns()
        self.last_timings_ns = {
            "preprocess_total": prepared - started,
            "inference": inferred - prepared,
            "confidence_decode_nms": filtered - inferred,
            "coordinate_restoration_and_detection_creation": restored - filtered,
            "detection_batch_creation": completed - restored,
            "end_to_end": completed - started,
        }
        return batch


class YoloXDetector(EdgeOnnxDetector):
    model_id = "yolox-nano"


class PicoDetDetector(EdgeOnnxDetector):
    model_id = "picodet-s"
