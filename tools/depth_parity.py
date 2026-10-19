"""Optional fixed-shape local export experiment; not an inference-provider promise."""

import argparse
import importlib
import json
from pathlib import Path

import av
import numpy as np

from perception_lab.depth_config import DepthConfig
from perception_lab.depth_runtime import DepthAnythingProvider
from perception_lab.detector_runtime import file_hash


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.model / "sentinel-manifest.json").read_text())
    a = manifest["artifacts"]
    model = DepthAnythingProvider(
        DepthConfig(
            provider="dav2_relative",
            weights=str((args.model / "model.safetensors").resolve()),
            sha256=a["model.safetensors"]["sha256"],
            config_sha256=a["config.json"]["sha256"],
            processor_sha256=a["preprocessor_config.json"]["sha256"],
        ),
        Path.cwd(),
    )
    torch = model.torch
    with av.open(str(args.image)) as container:
        pixels = next(container.decode(video=0)).to_ndarray(format="rgb24")
    tensor = model.processor(
        images=pixels, return_tensors="pt", size={"height": 266, "width": 266}
    )["pixel_values"]

    class Export(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.depth = model.model

        def forward(self, pixel_values):
            return self.depth(pixel_values=pixel_values).predicted_depth

    wrapper = Export().eval()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with torch.inference_mode():
        native = wrapper(tensor).numpy()
        torch.onnx.export(
            wrapper,
            (tensor,),
            str(args.output),
            input_names=["pixel_values"],
            output_names=["depth"],
            opset_version=18,
            dynamo=False,
        )
    ort = importlib.import_module("onnxruntime")
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(args.output), options, providers=["CPUExecutionProvider"])
    exported = session.run(None, {"pixel_values": tensor.numpy()})[0]
    absolute = np.abs(exported - native)
    passed = bool(np.allclose(exported, native, rtol=0.001, atol=0.001))
    report = {
        "status": "PASS" if passed else "FAIL",
        "scope": "one real frame, CPU FP32 fixed shape; not broad parity qualification",
        "input_shape": list(tensor.shape),
        "sha256": file_hash(args.output),
        "native_weight_sha256": a["model.safetensors"]["sha256"],
        "image_sha256": file_hash(args.image),
        "rtol": 0.001,
        "atol": 0.001,
        "max_absolute_error": float(absolute.max()),
        "mean_absolute_error": float(absolute.mean()),
        "finite_mask_equal": bool(np.array_equal(np.isfinite(native), np.isfinite(exported))),
        "native_percentiles": np.percentile(native, [25, 50, 75]).tolist(),
        "onnx_percentiles": np.percentile(exported, [25, 50, 75]).tolist(),
    }
    args.output.with_suffix(".parity.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    if not passed:
        raise ValueError("Native/ONNX tolerance failed")


if __name__ == "__main__":
    main()
