"""Local-only optional Transformers boundary; vendor objects never leave this module."""

import importlib
import os
from pathlib import Path
from time import perf_counter_ns
from typing import Any

import numpy as np

from .config import canonical_hash
from .contracts import ComponentProvenance, FrameIdentity, PixelFormat
from .depth import DepthAxis, DepthDirection, DepthFrame, DepthKind, DepthRepresentation
from .depth_config import DepthConfig
from .detector_runtime import file_hash
from .offline import enforce_offline
from .preprocessing import PreparedImage


class DepthAnythingProvider:
    def __init__(self, config: DepthConfig, base: Path) -> None:
        if config.provider == "synthetic" or config.weights is None:
            raise ValueError("Expected a real depth provider")
        weights = base / config.weights
        if weights.name != "model.safetensors":
            raise ValueError("Only local safetensors depth checkpoints supported")
        for path, digest in (
            (weights, config.sha256),
            (weights.parent / "config.json", config.config_sha256),
            (weights.parent / "preprocessor_config.json", config.processor_sha256),
        ):
            if not path.is_file() or file_hash(path) != digest:
                raise ValueError("Depth artifact hash mismatch")
        enforce_offline()
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
        os.environ["DO_NOT_TRACK"] = "1"
        self.torch: Any = importlib.import_module("torch")
        vendor: Any = importlib.import_module("transformers")
        self.torch.set_num_threads(config.threads)
        self.processor: Any = vendor.DPTImageProcessor.from_pretrained(
            str(weights.parent), local_files_only=True
        )
        self.model: Any = vendor.DepthAnythingForDepthEstimation.from_pretrained(
            str(weights.parent), local_files_only=True, use_safetensors=True
        ).eval()
        metric = config.provider == "dav2_metric_outdoor"
        expected = "metric" if metric else "relative"
        if self.model.config.depth_estimation_type != expected:
            raise ValueError("Depth checkpoint representation mismatch")
        if self.processor.do_pad:
            raise ValueError("Unimplemented depth padding mapping")
        self.representation = DepthRepresentation(
            DepthKind.METRIC if metric else DepthKind.RELATIVE,
            DepthDirection.LARGER_IS_FARTHER if metric else DepthDirection.LARGER_IS_NEARER,
            DepthAxis.CAMERA_Z if metric else DepthAxis.NONE,
            maximum=float(self.model.config.max_depth) if metric else None,
        )
        self.config = config
        self.provenance = ComponentProvenance(
            config.provider,
            "depth",
            config.provider,
            config.sha256,
            "transformers:" + str(vendor.__version__),
            canonical_hash(config.model_dump(exclude={"weights"})),
        )
        self.last_timings_ns: dict[str, int] = {}

    def estimate_depth(self, image: PreparedImage, identity: FrameIdentity) -> DepthFrame:
        if image.descriptor.pixel_format != PixelFormat.RGB or image.descriptor.layout != "NHWC":
            raise ValueError("Depth requires RGB NHWC")
        started = perf_counter_ns()
        inputs = self.processor(
            images=image.pixels,
            return_tensors="pt",
            size={"height": self.config.input_size, "width": self.config.input_size},
        )
        prepared = perf_counter_ns()
        with self.torch.inference_mode():
            output = self.model(**inputs).predicted_depth[0]
        inferred = perf_counter_ns()
        values = np.asarray(output.detach().cpu().numpy(), dtype=np.float32)
        # Keep native output resolution; Java composes its exact resize mapping.
        mapping = image.mapping.scaled(int(values.shape[1]), int(values.shape[0]))
        frame = DepthFrame(
            identity,
            self.representation,
            values,
            np.ones(values.shape, dtype=np.bool_),
            mapping,
            self.provenance,
            started,
            perf_counter_ns(),
        )
        self.last_timings_ns = {
            "preprocess": prepared - started,
            "runtime": inferred - prepared,
            "map_conversion": perf_counter_ns() - inferred,
        }
        return frame
