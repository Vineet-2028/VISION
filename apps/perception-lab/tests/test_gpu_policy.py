"""GPU opt-in must never silently become an unreported CPU session."""

import hashlib
from types import SimpleNamespace

import numpy as np
import pytest

from perception_lab import edge_runtime, semantic_runtime
from perception_lab.semantic_config import SemanticConfig


@pytest.mark.parametrize("kind", ["detector", "semantic"])
@pytest.mark.parametrize("policy", ["cpu", "cuda", "missing", "fallback"])
def test_explicit_provider_policy(monkeypatch, tmp_path, geometry, kind, policy):
    # Network denial is process-wide and separately tested in an isolated subprocess.
    monkeypatch.setattr(edge_runtime, "enforce_offline", lambda: None)
    path = tmp_path / "fixture.onnx"
    path.write_bytes(b"fixture; no real inference")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    constructions = []
    disabled = []
    selected = ["CPUExecutionProvider"]
    if policy == "cuda":
        selected.insert(0, "CUDAExecutionProvider")
    session = SimpleNamespace(
        run=lambda names, feed: (
            [np.empty((0, 6), dtype=np.float32)]
            if kind == "detector"
            else [np.zeros((1, 256, 512), dtype=np.int64)]
        ),
        get_providers=lambda: selected,
        disable_fallback=lambda: disabled.append(True),
        get_inputs=lambda: [
            SimpleNamespace(name="image", type="tensor(float)", shape=[1, 3, 256, 512])
        ],
        get_outputs=lambda: [SimpleNamespace(name="labels")],
    )

    def construct(*args, **kwargs):
        constructions.append(kwargs["providers"])
        return session

    ort = SimpleNamespace(
        __version__="fixture",
        SessionOptions=SimpleNamespace,
        ExecutionMode=SimpleNamespace(ORT_SEQUENTIAL=0),
        InferenceSession=construct,
        get_available_providers=lambda: (
            ["CPUExecutionProvider"]
            if policy == "missing"
            else ["CUDAExecutionProvider", "CPUExecutionProvider"]
        ),
    )
    cv = semantic_runtime.cv2
    monkeypatch.setattr(
        edge_runtime.importlib, "import_module", lambda name: ort if name == "onnxruntime" else cv
    )
    monkeypatch.setitem(edge_runtime.PINS, "picodet-s", digest)
    device = "cpu" if policy == "cpu" else "cuda:0"

    def create():
        if kind == "detector":
            return edge_runtime.PicoDetDetector(path, digest, device=device)
        return semantic_runtime.OnnxSemanticSegmenter(
            SemanticConfig(provider="pidnet", weights=path.name, sha256=digest, device=device),
            tmp_path,
            "fixture",
        )

    if policy in {"missing", "fallback"}:
        with pytest.raises(ValueError, match="unavailable" if policy == "missing" else "fell back"):
            create()
        assert len(constructions) == (0 if policy == "missing" else 1)
    else:
        adapter = create()
        assert adapter.session is session
        from perception_lab.config import PreprocessConfig
        from perception_lab.preprocessing import BasicPreprocessor
        from perception_lab.sources import SyntheticSource

        for frame in SyntheticSource(iter([0, 100_000_000])):
            image = BasicPreprocessor(geometry, PreprocessConfig()).prepare(frame)
            method = adapter.detect if kind == "detector" else adapter.segment
            method(image, frame.identity)
        assert constructions == [
            ["CPUExecutionProvider"]
            if policy == "cpu"
            else [("CUDAExecutionProvider", {"use_tf32": "0"}), "CPUExecutionProvider"]
        ]
    assert disabled == ([True] if policy in {"cuda", "fallback"} else [])


def test_synthetic_provider_cannot_claim_cuda():
    with pytest.raises(ValueError, match="cannot claim GPU"):
        SemanticConfig(device="cuda:0")
