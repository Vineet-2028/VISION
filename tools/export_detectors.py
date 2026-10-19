"""Explicit local FP32/static/batch-one ONNX research export. No auto-downloads."""

import argparse
import json
from pathlib import Path

from perception_lab.detector_runtime import UltralyticsDetector, file_hash
from perception_lab.offline import enforce_offline
from perception_lab.rtdetr_runtime import RtDetrDetector


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--runtime", choices=("ultralytics", "rtdetr"), default="ultralytics")
    args = parser.parse_args()
    if file_hash(args.weights) != args.sha256:
        raise ValueError("Checkpoint integrity mismatch")
    target = args.weights.with_suffix(".onnx")
    if target.exists():
        raise ValueError("Refusing to overwrite an exported artifact")
    enforce_offline()
    if args.runtime == "rtdetr":
        detector = RtDetrDetector(args.weights, args.sha256)
        torch = detector.torch

        class Outputs(torch.nn.Module):
            def __init__(self, model):
                super().__init__()
                self.model = model

            def forward(self, pixels):
                result = self.model(pixel_values=pixels)
                return result.logits, result.pred_boxes

        with torch.inference_mode():
            torch.onnx.export(
                Outputs(detector.model).eval(),
                torch.zeros(1, 3, 640, 640),
                str(target),
                input_names=["pixel_values"],
                output_names=["logits", "pred_boxes"],
                opset_version=17,
                dynamo=False,
            )
        exported = target
    else:
        detector = UltralyticsDetector(args.weights, args.sha256)
        exported = Path(
            detector.model.export(
                format="onnx",
                imgsz=640,
                batch=1,
                device="cpu",
                opset=17,
                dynamic=False,
                simplify=False,
                nms=None,
            )
        )
    import onnx

    onnx.checker.check_model(str(exported), full_check=True)
    model = onnx.load(str(exported))
    result = {
        "schema_version": 1,
        "source_sha256": args.sha256,
        "sha256": file_hash(exported),
        "opsets": {item.domain: item.version for item in model.opset_import},
        "inputs": {
            item.name: [d.dim_value or d.dim_param for d in item.type.tensor_type.shape.dim]
            for item in model.graph.input
        },
        "outputs": {
            item.name: [d.dim_value or d.dim_param for d in item.type.tensor_type.shape.dim]
            for item in model.graph.output
        },
        "bytes": exported.stat().st_size,
        "checker": "PASS",
        "numerical_parity": "NOT_YET_TESTED",
        "precision": "FP32",
        "batch": 1,
        "dynamic": False,
    }
    with exported.with_suffix(".export.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
