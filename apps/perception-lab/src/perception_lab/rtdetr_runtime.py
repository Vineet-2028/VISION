"""Optional local-only boundary for the official converted RT-DETRv2 R18 checkpoint."""

import importlib
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from .clocks import processing_ns
from .config import canonical_hash
from .contracts import ComponentProvenance, FailureSeverity, FrameIdentity, LabError, PixelFormat
from .detection import Box, Detection, DetectionBatch, semantic_class
from .detector_runtime import file_hash
from .offline import enforce_offline
from .preprocessing import PreparedImage


class RtDetrDetector:
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
        if weights.name not in {"model.safetensors", "model.onnx"} or not weights.is_file():
            raise ValueError("Expected local RT-DETR safetensors or ONNX checkpoint")
        if file_hash(weights) != sha256:
            raise ValueError("Checkpoint hash mismatch")
        if size not in {512, 640, 768} or not 0 <= confidence <= 1 or not 1 <= threads <= 16:
            raise ValueError("Invalid detector configuration")
        if device not in {"cpu", "cuda:0"} or (half and device == "cpu"):
            raise ValueError("Unsupported device/precision")
        if weights.suffix == ".onnx" and (device != "cpu" or size != 640):
            raise ValueError("RT-DETR ONNX currently requires static 640 CPU FP32")
        enforce_offline()
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
        os.environ["DO_NOT_TRACK"] = "1"
        vendor: Any = importlib.import_module("transformers")
        self.torch: Any = importlib.import_module("torch")
        self.torch.manual_seed(0)
        self.torch.set_num_threads(threads)
        if device != "cpu" and not self.torch.cuda.is_available():
            raise ValueError("Requested CUDA device is unavailable")
        directory = str(weights.resolve().parent)
        self.processor: Any = vendor.RTDetrImageProcessor.from_pretrained(
            directory, local_files_only=True
        )
        self.session: Any = None
        self.model: Any = None
        if weights.suffix == ".onnx":
            ort: Any = importlib.import_module("onnxruntime")
            options = ort.SessionOptions()
            options.intra_op_num_threads = threads
            options.inter_op_num_threads = 1
            options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            self.session = ort.InferenceSession(
                str(weights.resolve()), options, providers=["CPUExecutionProvider"]
            )
            config = vendor.RTDetrV2Config.from_pretrained(directory, local_files_only=True)
        else:
            self.model = (
                vendor.RTDetrV2ForObjectDetection.from_pretrained(
                    directory, local_files_only=True, use_safetensors=True
                )
                .eval()
                .to(device)
            )
            if half:
                self.model.half()
            config = self.model.config
        self.names: dict[int, str] = dict(config.id2label)
        if len(self.names) != 80 or self.names.get(0) != "person" or self.names.get(16) != "dog":
            raise ValueError("Expected COCO-80 model")
        self.size, self.confidence, self.device, self.half = size, confidence, device, half
        self.threads = threads
        self.last_timings_ns: dict[str, int] = {}
        self.runtime_metadata: dict[str, object] = {
            "torch_version": str(self.torch.__version__),
            "torch_threads": self.torch.get_num_threads(),
            "seed": 0,
            "nms_mode": "NMS_FREE",
            "artifact_format": weights.suffix.lstrip("."),
            "parameter_count": sum(p.numel() for p in self.model.parameters())
            if self.model is not None
            else None,
            "providers": self.session.get_providers() if self.session is not None else ["PyTorch"],
        }
        self.provenance = ComponentProvenance(
            "RtDetrDetector",
            "detector",
            "rtdetr-v2-r18",
            sha256,
            f"transformers-{vendor.__version__}/{weights.suffix}/{device}/"
            f"{'fp16' if half else 'fp32'}",
            canonical_hash(
                {
                    "files": {
                        name: file_hash(weights.parent / name)
                        for name in ("config.json", "preprocessor_config.json")
                    },
                    "size": size,
                    "confidence": confidence,
                    "device": device,
                    "half": half,
                    "threads": threads,
                }
            ),
        )

    def synchronize(self) -> None:
        if self.device != "cpu":
            self.torch.cuda.synchronize()

    def detect(self, image: PreparedImage, identity: FrameIdentity) -> DetectionBatch:
        if image.descriptor.pixel_format != PixelFormat.RGB or image.descriptor.layout != "NHWC":
            raise ValueError("Detector requires RGB NHWC")
        self.synchronize()
        started = processing_ns()
        self.torch.set_num_threads(self.threads)
        try:
            inputs = self.processor(
                images=image.pixels,
                return_tensors="pt",
                size={"height": self.size, "width": self.size},
            )
            inputs = inputs.to(self.device)
            if self.half:
                inputs["pixel_values"] = inputs["pixel_values"].half()
            self.synchronize()
            prepared = processing_ns()
            with self.torch.inference_mode():
                if self.session is None:
                    result = self.model(**inputs)
                else:
                    logits, boxes = self.session.run(
                        ["logits", "pred_boxes"], {"pixel_values": inputs["pixel_values"].numpy()}
                    )
                    result = SimpleNamespace(
                        logits=self.torch.from_numpy(logits),
                        pred_boxes=self.torch.from_numpy(boxes),
                    )
            self.synchronize()
            inferred = processing_ns()
            result = self.processor.post_process_object_detection(
                result,
                threshold=self.confidence,
                target_sizes=[(image.descriptor.height, image.descriptor.width)],
            )[0]
            self.synchronize()
            filtered = processing_ns()
            boxes = result["boxes"].cpu().tolist()
            scores = result["scores"].cpu().tolist()
            labels = result["labels"].cpu().tolist()
            transferred = processing_ns()
            classes = tuple(
                (int(label), self.names[int(label)], semantic_class(self.names[int(label)]))
                for label in labels
            )
            classified = processing_ns()
            detections = tuple(
                Detection(
                    label[0],
                    label[1],
                    label[2],
                    float(score),
                    image.mapping.restore_box(Box(*[float(v) for v in box])),
                )
                for box, score, label in zip(
                    boxes,
                    scores,
                    classes,
                    strict=True,
                )
            )
            self.synchronize()
            completed = processing_ns()
            batch = DetectionBatch(
                identity,
                detections,
                self.provenance,
                image.mapping.fingerprint,
                inferred - prepared,
                completed - inferred,
            )
            batched = processing_ns()
            self.last_timings_ns = {
                "vendor_preprocess": prepared - started,
                "preprocess_total": prepared - started,
                "inference": inferred - prepared,
                "confidence_filter_and_box_scaling": filtered - inferred,
                "output_transfer": transferred - filtered,
                "class_mapping": classified - transferred,
                "coordinate_restoration_and_detection_creation": completed - classified,
                "detection_batch_creation": batched - completed,
                "postprocess_total": batched - inferred,
                "end_to_end": batched - started,
            }
            return batch
        except (MemoryError, self.torch.cuda.OutOfMemoryError) as error:
            raise LabError("DETECTOR_OUT_OF_MEMORY", FailureSeverity.RECOVERABLE) from error
