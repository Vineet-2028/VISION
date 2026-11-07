"""Local ONNX adapters. Foreign runtime objects stay inside this boundary."""

import hashlib
import importlib
from pathlib import Path
from time import perf_counter_ns
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from .config import canonical_hash
from .contracts import ComponentProvenance, FailureSeverity, FrameIdentity, LabError, PixelFormat
from .preprocessing import PreparedImage
from .semantic_config import SemanticConfig
from .semantics import SemanticClass as C
from .semantics import SemanticFrame

# Cityscapes train IDs 0..18. "terrain" is broad GROUND_OTHER, not confidently GRASS.
# Traffic signs/lights are OBJECT_OTHER; sky is BACKGROUND_OTHER. Stairs/curb unsupported.
CITYSCAPES_V1 = (
    C.ROAD,
    C.SIDEWALK,
    C.BUILDING,
    C.WALL,
    C.FENCE,
    C.POLE,
    C.OBJECT_OTHER,
    C.OBJECT_OTHER,
    C.VEGETATION,
    C.GROUND_OTHER,
    C.BACKGROUND_OTHER,
    C.PERSON,
    C.PERSON,
    C.VEHICLE,
    C.VEHICLE,
    C.VEHICLE,
    C.VEHICLE,
    C.MOTORCYCLE,
    C.BICYCLE,
)


def map_cityscapes(labels: NDArray[np.int64]) -> NDArray[np.uint8]:
    if labels.ndim != 2 or not np.all((labels >= 0) & (labels < len(CITYSCAPES_V1))):
        raise ValueError("Unexpected Cityscapes train ID")
    return np.asarray(CITYSCAPES_V1, dtype=np.uint8)[labels]


def require_rgb(image: PreparedImage) -> None:
    if (
        image.descriptor.pixel_format != PixelFormat.RGB
        or image.descriptor.layout != "NHWC"
        or image.pixels.shape != (image.descriptor.height, image.descriptor.width, 3)
        or image.mapping.target_dimensions != (image.descriptor.width, image.descriptor.height)
    ):
        raise ValueError("Semantic adapter requires mapped RGB NHWC pixels")


class SyntheticSegmenter:
    provenance = ComponentProvenance("SyntheticSegmenter", "segmentation", model_id="analytical")

    def __init__(self, session_id: str, pattern: str = "split") -> None:
        if pattern not in {"sidewalk", "split", "path", "stairs", "unknown", "dynamic"}:
            raise ValueError("Unknown synthetic pattern")
        self.session_id, self.pattern = session_id, pattern

    def segment(self, image: PreparedImage, identity: FrameIdentity) -> SemanticFrame:
        require_rgb(image)
        start = perf_counter_ns()
        h, w = image.pixels.shape[:2]
        labels = np.full((h, w), C.SIDEWALK, dtype=np.uint8)
        if self.pattern == "unknown":
            labels.fill(C.UNKNOWN)
        elif self.pattern == "split":
            labels[: h // 2] = C.ROAD
        elif self.pattern == "path":
            labels.fill(C.WALL)
            labels[:, w // 3 : 2 * w // 3] = C.PATH
        elif self.pattern == "stairs":
            labels[h // 3 : 2 * h // 3] = C.STAIRS
        elif self.pattern == "dynamic":
            labels[h // 3 : 2 * h // 3, w // 3 : 2 * w // 3] = C.PERSON
        return SemanticFrame(
            self.session_id,
            identity,
            identity,
            labels,
            image.mapping,
            self.provenance,
            frozenset(C),
            start,
            perf_counter_ns(),
        )


class OnnxSemanticSegmenter:
    """Reviewed ONNX export profiles only; no remote code or implicit model downloads."""

    def __init__(self, config: SemanticConfig, base: Path, session_id: str) -> None:
        if config.provider == "synthetic" or config.weights is None:
            raise ValueError("Real ONNX configuration required")
        path = (base / config.weights).resolve()
        with path.open("rb") as handle:
            if hashlib.file_digest(handle, "sha256").hexdigest() != config.sha256:
                raise ValueError("Semantic checkpoint hash mismatch")
        ort: Any = importlib.import_module("onnxruntime")
        options = ort.SessionOptions()
        options.intra_op_num_threads = config.threads
        options.inter_op_num_threads = 1
        providers: list[Any] = ["CPUExecutionProvider"]
        if config.device == "cuda:0":
            if "CUDAExecutionProvider" not in ort.get_available_providers():
                raise ValueError("CUDA was requested but the execution provider is unavailable")
            providers.insert(0, ("CUDAExecutionProvider", {"use_tf32": "0"}))
        self.session: Any = ort.InferenceSession(
            str(path), sess_options=options, providers=providers
        )
        if config.device == "cuda:0":
            self.session.disable_fallback()
            if "CUDAExecutionProvider" not in self.session.get_providers():
                raise ValueError("CUDA initialization fell back to CPU")
        inputs = self.session.get_inputs()
        if len(inputs) != 1 or inputs[0].type != "tensor(float)":
            raise ValueError("Unsupported semantic input signature")
        expected = [1, 3, config.height, config.width]
        if len(inputs[0].shape) != 4 or any(
            isinstance(value, int) and value != target
            for value, target in zip(inputs[0].shape, expected, strict=True)
        ):
            raise ValueError("Semantic model input dimensions disagree with configuration")
        if len(self.session.get_outputs()) != 1:
            raise ValueError("Export must expose exactly one semantic prediction")
        self.input_name = str(inputs[0].name)
        self.config, self.session_id = config, session_id
        self.provenance = ComponentProvenance(
            config.provider,
            "segmentation",
            model_id=config.provider,
            model_version=config.sha256,
            runtime="onnxruntime-" + ort.__version__ + "/" + config.device,
            configuration_hash=canonical_hash(
                config.model_dump(
                    exclude={"weights", "device"} if config.device == "cpu" else {"weights"}
                )
            ),
        )
        self.stage_ns: dict[str, int] = {}

    def segment(self, image: PreparedImage, identity: FrameIdentity) -> SemanticFrame:
        require_rgb(image)
        start = perf_counter_ns()
        c = self.config
        pixels = cv2.resize(image.pixels, (c.width, c.height), interpolation=cv2.INTER_LINEAR)
        values: NDArray[np.float32] = pixels.astype(np.float32) / np.float32(255)
        if c.provider == "pidnet":
            values -= np.array([0.485, 0.456, 0.406], dtype=np.float32)
            values /= np.array([0.229, 0.224, 0.225], dtype=np.float32)
        else:
            values = (values - np.float32(0.5)) / np.float32(0.5)
        tensor = np.ascontiguousarray(values.transpose(2, 0, 1)[None])
        pre = perf_counter_ns()
        try:
            output = np.asarray(self.session.run(None, {self.input_name: tensor})[0])
        except Exception:
            raise LabError("SEGMENTATION_INFERENCE_FAILED", FailureSeverity.RECOVERABLE) from None
        inferred = perf_counter_ns()
        if c.output_kind == "logits_nchw":
            if (
                output.ndim != 4
                or output.shape[0] != 1
                or output.shape[1] != 19
                or output.size > 19 * 2048 * 1024
                or not np.isfinite(output).all()
            ):
                raise ValueError("Invalid segmentation logits")
            native = np.argmax(output[0], axis=0).astype(np.int64)
        else:
            if output.ndim == 3 and output.shape[0] == 1:
                output = output[0]
            if (
                output.ndim != 2
                or output.size > 2048 * 1024
                or not np.issubdtype(output.dtype, np.integer)
            ):
                raise ValueError("Invalid segmentation label tensor")
            native = output.astype(np.int64)
        labels = map_cityscapes(native)
        # Both operations are pure resize; compose their scale directly to the output grid.
        mapping = image.mapping.scaled(labels.shape[1], labels.shape[0])
        end = perf_counter_ns()
        self.stage_ns = {
            "preprocess": pre - start,
            "inference": inferred - pre,
            "postprocess": end - inferred,
        }
        return SemanticFrame(
            self.session_id,
            identity,
            identity,
            labels,
            mapping,
            self.provenance,
            frozenset(CITYSCAPES_V1),
            start,
            end,
            mapping_version="cityscapes-trainids-to-sentinel-v1",
        )
