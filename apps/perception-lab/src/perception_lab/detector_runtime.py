"""Optional Ultralytics boundary. No vendor objects escape this module.

Only explicitly supplied, hash-verified local weights are loaded. PyTorch checkpoints
are executable artifacts: their hash must come from a trusted acquisition manifest.
"""

import hashlib
import importlib
import os
from pathlib import Path
from typing import Any

import numpy as np

from .clocks import processing_ns
from .config import canonical_hash
from .contracts import ComponentProvenance, FailureSeverity, FrameIdentity, LabError, PixelFormat
from .detection import Box, Detection, DetectionBatch, semantic_class
from .offline import enforce_offline
from .preprocessing import PreparedImage


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class UltralyticsDetector:
    """Batch-one local research adapter; synchronous, owned by one pipeline thread."""

    def __init__(
        self,
        weights: Path,
        sha256: str,
        *,
        size: int = 640,
        confidence: float = 0.05,
        device: str = "cpu",
        half: bool = False,
        threads: int = 1,
    ) -> None:
        if weights.suffix not in {".pt", ".onnx"} or not weights.is_file():
            raise ValueError("An existing local .pt or .onnx checkpoint is required")
        if file_hash(weights) != sha256:
            raise ValueError("Checkpoint hash mismatch")
        if size not in {512, 640, 768} or not 0 <= confidence <= 1 or not 1 <= threads <= 16:
            raise ValueError("Invalid detector configuration")
        if device not in {"cpu", "cuda:0"} or (half and device == "cpu"):
            raise ValueError("Unsupported device/precision")
        if weights.suffix == ".onnx" and device != "cpu":
            raise ValueError("This ONNX adapter currently verifies CPUExecutionProvider only")
        # Vendor offline environment flags alone are not an enforceable network policy.
        enforce_offline()
        # Set before importing optional vendor modules. No telemetry or auto dependency installs.
        os.environ["YOLO_AUTOINSTALL"] = "False"
        os.environ["YOLO_OFFLINE"] = "True"
        os.environ["YOLO_VERBOSE"] = "False"
        settings_directory = weights.resolve().parent / "runtime-settings"
        # The vendor falls back to CWD if this parent does not exist yet.
        settings_directory.mkdir(parents=True, exist_ok=True)
        os.environ["YOLO_CONFIG_DIR"] = str(settings_directory)
        vendor: Any = importlib.import_module("ultralytics")
        self.torch: Any = importlib.import_module("torch")
        self.torch.manual_seed(0)
        vendor.settings.update({"sync": False})
        self.torch.set_num_threads(threads)
        if device == "cuda:0" and not self.torch.cuda.is_available():
            raise ValueError("Requested CUDA device is unavailable")
        self.model: Any = vendor.YOLO(str(weights.resolve()), task="detect")
        torch = self.torch
        nms_module: Any = importlib.import_module("ultralytics.utils.nms")
        predictor_module: Any = importlib.import_module("ultralytics.models.yolo.detect")
        results_module: Any = importlib.import_module("ultralytics.engine.results")
        cv2: Any = importlib.import_module("cv2")
        stage_timings: dict[str, int] = {}

        # Pinned vendor extension point: setup_device otherwise resets torch CPU threads.
        class ControlledPredictor(predictor_module.DetectionPredictor):  # type: ignore[misc]
            def preprocess(self, images: Any) -> Any:
                if len(images) != 1 or self.args.rect or self.scale_fill:
                    raise ValueError("Expected fixed square batch-one letterbox")
                image = images[0]
                started = processing_ns()
                ratio = min(size / image.shape[1], size / image.shape[0])
                w, h = max(1, round(image.shape[1] * ratio)), max(1, round(image.shape[0] * ratio))
                resized = cv2.resize(image, (w, h), interpolation=cv2.INTER_LINEAR)
                resized_at = processing_ns()
                left, top = (size - w) // 2, (size - h) // 2
                padded = cv2.copyMakeBorder(
                    resized,
                    top,
                    size - h - top,
                    left,
                    size - w - left,
                    cv2.BORDER_CONSTANT,
                    value=(114, 114, 114),
                )
                padded_at = processing_ns()
                rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
                colored_at = processing_ns()
                tensor = (
                    torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0).contiguous().to(self.device)
                )
                if device != "cpu":
                    torch.cuda.synchronize()
                tensor_at = processing_ns()
                tensor = tensor.half() if self.model.fp16 else tensor.float()
                tensor.div_(255.0)
                if device != "cpu":
                    torch.cuda.synchronize()
                normalized_at = processing_ns()
                stage_timings.update(
                    {
                        "resize": resized_at - started,
                        "letterbox": padded_at - resized_at,
                        "model_color_conversion": colored_at - padded_at,
                        "tensor_creation_transfer": tensor_at - colored_at,
                        "normalization": normalized_at - tensor_at,
                    }
                )
                return tensor

            def construct_result(self, pred: Any, img: Any, original: Any, path: Any) -> Any:
                # Keep raw model-space boxes private until the adapter's exact Java inverse.
                return results_module.Results(
                    original, path=path, names=self.model.names, boxes=pred[:, :6]
                )

            def postprocess(self, preds: Any, img: Any, orig_imgs: Any, **kwargs: Any) -> Any:
                # Pinned detect-only path. Vendor NMS includes score filtering; do not
                # mislabel this as the pure suppression kernel or enable tracking features.
                started = processing_ns()
                suppressed = nms_module.non_max_suppression(
                    preds,
                    self.args.conf,
                    self.args.iou,
                    self.args.classes,
                    self.args.agnostic_nms,
                    max_det=self.args.max_det,
                    nc=0,
                    end2end=getattr(self.model, "end2end", False),
                    rotated=False,
                )
                if device != "cpu":
                    torch.cuda.synchronize()
                stage_timings["nms_with_confidence_filter"] = processing_ns() - started
                return self.construct_results(suppressed, img, orig_imgs)

            def setup_model(self, model: Any, verbose: bool = True) -> None:
                super().setup_model(model, verbose=verbose)
                torch.set_num_threads(threads)
                if weights.suffix == ".onnx":
                    ort: Any = importlib.import_module("onnxruntime")
                    options = ort.SessionOptions()
                    options.intra_op_num_threads = threads
                    options.inter_op_num_threads = 1
                    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
                    # CPU uses session.run, not device-specific IO bindings.
                    self.model.backend.session = ort.InferenceSession(
                        str(weights.resolve()), options, providers=["CPUExecutionProvider"]
                    )

        self.model.predictor = ControlledPredictor(
            overrides={
                "device": device,
                "imgsz": size,
                "conf": confidence,
                "half": half,
                "rect": False,
                "batch": 1,
                "verbose": False,
                "save": False,
            }
        )
        self.predictor_type = ControlledPredictor
        self.model.predictor.setup_model(self.model.model, verbose=False)
        self.runtime_metadata: dict[str, object] = {
            "torch_version": str(torch.__version__),
            "torch_threads": torch.get_num_threads(),
            "seed": 0,
            "nms_mode": "external_one_to_many",
            "artifact_format": weights.suffix,
            "parameter_count_loaded": sum(p.numel() for p in self.model.model.parameters())
            if weights.suffix == ".pt"
            else None,
            "providers": self.model.predictor.model.backend.session.get_providers()
            if weights.suffix == ".onnx"
            else ["PyTorch"],
        }
        names = self.model.names
        expected = {
            0: "person",
            1: "bicycle",
            2: "car",
            3: "motorcycle",
            5: "bus",
            6: "train",
            7: "truck",
            16: "dog",
        }
        if len(names) != 80 or any(names.get(k) != v for k, v in expected.items()):
            raise ValueError("Expected verified COCO-80 class names")
        self.size, self.confidence, self.device, self.half = size, confidence, device, half
        self.threads = threads
        self.provenance = ComponentProvenance(
            "UltralyticsDetector",
            "detector",
            weights.stem,
            sha256,
            f"ultralytics-{vendor.__version__}/{device}/{'fp16' if half else 'fp32'}",
            canonical_hash(
                {
                    "size": size,
                    "confidence": confidence,
                    "threads": threads,
                    "device": device,
                    "half": half,
                    "nms_iou": 0.7,
                    "max_det": 300,
                }
            ),
        )
        self.last_timings_ns: dict[str, int] = {}
        self._stage_timings = stage_timings

    def detect(self, image: PreparedImage, identity: FrameIdentity) -> DetectionBatch:
        if image.descriptor.pixel_format != PixelFormat.RGB or image.descriptor.layout != "NHWC":
            raise ValueError("Detector requires uint8 RGB NHWC prepared image")
        if self.device != "cpu":
            self.torch.cuda.synchronize()
        start = processing_ns()
        # JNI/native initialization may change the calling thread's OpenMP state.
        self.torch.set_num_threads(self.threads)
        model_mapping, _ = image.mapping.letterboxed(self.size, self.size)
        geometry_at = processing_ns()
        # Vendor ndarray loader expects BGR; our predictor retains raw tensor-space boxes.
        bgr = np.ascontiguousarray(image.pixels[:, :, ::-1])
        converted = processing_ns()
        try:
            results = self.model.predict(
                predictor=self.predictor_type,
                source=bgr,
                imgsz=self.size,
                conf=self.confidence,
                iou=0.7,
                device=self.device,
                half=self.half,
                rect=False,
                batch=1,
                max_det=300,
                verbose=False,
                save=False,
                stream=False,
            )
            if self.device != "cpu":
                self.torch.cuda.synchronize()
            inferred = processing_ns()
            if self.torch.get_num_threads() != self.threads:
                raise ValueError("Runtime changed CPU thread configuration during inference")
            if len(results) != 1:
                raise ValueError("Expected batch one")
            result = results[0]
            if tuple(result.orig_shape) != (image.descriptor.height, image.descriptor.width):
                raise ValueError("Vendor output coordinate space mismatch")
            rows = result.boxes.data.detach().cpu().tolist()
            transferred = processing_ns()
            labels = tuple(
                (
                    int(row[5]),
                    str(result.names[int(row[5])]),
                    semantic_class(str(result.names[int(row[5])])),
                )
                for row in rows
            )
            classified = processing_ns()
            detections = tuple(
                Detection(
                    label[0],
                    label[1],
                    label[2],
                    float(row[4]),
                    model_mapping.restore_box(Box(*[float(v) for v in row[:4]])),
                )
                for row, label in zip(rows, labels, strict=True)
            )
            restored = processing_ns()
            speed = result.speed
            pre = int(float(speed["preprocess"]) * 1_000_000)
            infer = int(float(speed["inference"]) * 1_000_000)
            post = int(float(speed["postprocess"]) * 1_000_000)
            batch_started = processing_ns()
            batch = DetectionBatch(
                identity,
                detections,
                self.provenance,
                model_mapping.fingerprint,
                infer,
                post + restored - inferred,
            )
            completed = processing_ns()
            self.last_timings_ns = {
                **self._stage_timings,
                "geometry_setup": geometry_at - start,
                "color_conversion": converted - geometry_at,
                "vendor_preprocess": pre,
                "preprocess_total": converted - start + pre,
                "inference": infer,
                "vendor_postprocess": post,
                "output_transfer": transferred - inferred,
                "class_mapping": classified - transferred,
                "coordinate_restoration_and_detection_creation": restored - classified,
                "detection_batch_creation": completed - batch_started,
                "postprocess_total": post + completed - inferred,
                "vendor_call": inferred - converted,
                "end_to_end": completed - start,
            }
            return batch
        except (MemoryError, self.torch.cuda.OutOfMemoryError) as error:
            raise LabError("DETECTOR_OUT_OF_MEMORY", FailureSeverity.RECOVERABLE) from error
