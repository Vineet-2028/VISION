"""Export inspected official PIDNet-S source/checkpoint; never deserialize arbitrary pickle."""

import argparse
import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path

import numpy as np

SOURCE_HASHES = {
    "pidnet.py": "1692ebc05ea4cc7096abd0b9a2e7e79543d878955af1a9d3d60e7973d6eb623d",
    "model_utils.py": "8817f6367b4c9d094b35cd606926f2937cef98469fff888e3773c1c95ca969aa",
}
WEIGHT_HASH = "b51aa935bdb64a0779d776f38267fd49f7cce59413910abbbf0a74934b3d7c01"


def export(directory, width, height, output):
    import onnxruntime as ort
    import torch

    if output.exists():
        raise ValueError("Preserve existing export")
    for name, digest in SOURCE_HASHES.items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Unreviewed upstream source")
    checkpoint = directory / "PIDNet_S_Cityscapes_val.pt"
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != WEIGHT_HASH:
        raise ValueError("Checkpoint hash mismatch")
    package = types.ModuleType("sentinel_pidnet_export")
    package.__path__ = [str(directory.resolve())]
    sys.modules[package.__name__] = package
    spec = importlib.util.spec_from_file_location(
        package.__name__ + ".pidnet", directory / "pidnet.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    torch.set_num_threads(1)
    torch.manual_seed(10)
    model = module.get_pred_model("pidnet_s", 19).eval()
    weights = torch.load(checkpoint, map_location="cpu", weights_only=True)
    weights = weights.get("state_dict", weights)
    normalized = {k.removeprefix("model."): v for k, v in weights.items()}
    expected = model.state_dict()
    missing = set(expected) - set(normalized)
    extras = set(normalized) - set(expected)
    if missing or any(
        not k.startswith(("seghead_p.", "seghead_d.", "sb_loss.", "sem_loss.")) for k in extras
    ):
        raise ValueError(
            f"Unexpected checkpoint keys: missing={sorted(missing)}, extra={sorted(extras)}"
        )
    model.load_state_dict({k: normalized[k] for k in expected}, strict=True)

    class Export(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.network = model

        def forward(self, x):
            # Continuous logits are interpolated before argmax, never integer labels.
            return torch.nn.functional.interpolate(
                self.network(x), size=(height, width), mode="bilinear", align_corners=False
            )

    wrapper = Export().eval()
    x = torch.randn(1, 3, height, width)
    with torch.inference_mode():
        reference = wrapper(x).numpy()
        torch.onnx.export(
            wrapper,
            x,
            output,
            input_names=["image"],
            output_names=["logits"],
            opset_version=17,
            dynamo=False,
        )
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    session = ort.InferenceSession(str(output), options, providers=["CPUExecutionProvider"])
    actual = session.run(None, {"image": x.numpy()})[0]
    agreement = float((actual.argmax(1) == reference.argmax(1)).mean())
    if agreement < 0.999:
        raise ValueError("Native/export parity failed")
    report = {
        "checkpoint_sha256": WEIGHT_HASH,
        "source_sha256": SOURCE_HASHES,
        "export_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "dimensions": [width, height],
        "seed": 10,
        "parity_scope": "one seeded synthetic tensor; not real-frame accuracy",
        "class_agreement": agreement,
        "maximum_logit_error": float(np.abs(actual - reference).max()),
    }
    output.with_suffix(".parity.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--width", type=int, choices=(512, 768), default=512)
    parser.add_argument("--height", type=int, choices=(256, 384), default=256)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    export(args.source, args.width, args.height, args.output)
