"""Isolated FP32 ONNX CPU/CUDA parity and actual node-placement experiment.

Optional research dependencies are imported only during execution. This does
not change application providers or claim a full dataset accuracy evaluation.
"""

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter_ns


def run(config_path, runtime, libraries, output, cudnn_directory=None, strict_fp32=False):
    import numpy as np

    sys.path.insert(0, str(runtime.resolve()))
    sys.path.append(str(libraries.resolve()))
    import onnxruntime as ort

    from perception_lab.config import Calibration, LabConfig, read_json
    from perception_lab.edge_runtime import PicoDetDetector
    from perception_lab.geometry import CoreGeometry
    from perception_lab.preprocessing import BasicPreprocessor
    from perception_lab.semantic_runtime import OnnxSemanticSegmenter
    from perception_lab.sources import VideoFileSource

    output.mkdir(parents=True, exist_ok=False)
    paths = [
        path
        for path in (libraries / "nvidia").glob("*/bin")
        if cudnn_directory is None or path.parent.name != "cudnn"
    ]
    if cudnn_directory is not None:
        paths.append(cudnn_directory)
    dll_directories = [os.add_dll_directory(str(path.resolve())) for path in paths]
    ort.preload_dlls(cudnn=cudnn_directory is None)
    if cudnn_directory is not None:
        ort.preload_dlls(cuda=False, cudnn=True, directory=str(cudnn_directory.resolve()))
    config = LabConfig.model_validate(read_json(config_path))
    base = config_path.resolve().parent
    geometry = CoreGeometry(Calibration.model_validate(read_json(base / config.calibration)))
    source = VideoFileSource(base / config.input, config.source_id, config.max_pixels)
    report = {
        "ort": ort.__version__,
        "available": ort.get_available_providers(),
        "cudnn_override": str(cudnn_directory) if cudnn_directory is not None else None,
        "strict_fp32": strict_fp32,
        "models": {},
    }

    class Capture:
        def __init__(self, session):
            self.session, self.feed, self.result = session, None, None

        def run(self, names, feed):
            self.feed = feed
            self.result = self.session.run(names, feed)
            return self.result

        def __getattr__(self, name):
            return getattr(self.session, name)

    try:
        frame = next(iter(source))
        image = BasicPreprocessor(geometry, config.preprocess).prepare(frame)
        detector = config.detector
        semantic = config.segmentation
        assert detector and semantic
        models = {
            "detector": (
                PicoDetDetector(
                    base / detector.weights,
                    detector.sha256,
                    size=detector.input_size,
                    confidence=detector.confidence,
                ),
                "detect",
                base / detector.weights,
            ),
            "segmentation": (
                OnnxSemanticSegmenter(semantic, base, "rescue-gpu-probe"),
                "segment",
                base / semantic.weights,
            ),
        }
        for name, (adapter, method, weights) in models.items():
            cpu = adapter.session
            capture = Capture(cpu)
            adapter.session = capture
            getattr(adapter, method)(image, frame.identity)
            options = ort.SessionOptions()
            options.intra_op_num_threads = 1
            options.inter_op_num_threads = 1
            options.enable_profiling = True
            options.profile_file_prefix = str(output / name)
            gpu = ort.InferenceSession(
                str(weights),
                options,
                providers=[
                    ("CUDAExecutionProvider", {"use_tf32": "0" if strict_fp32 else "1"}),
                    "CPUExecutionProvider",
                ],
            )
            timings = {}
            observed = None
            for label, session in (("cpu", cpu), ("cuda_requested", gpu)):
                session.run(None, capture.feed)
                samples = []
                for _ in range(10):
                    started = perf_counter_ns()
                    values = session.run(None, capture.feed)
                    samples.append(perf_counter_ns() - started)
                timings[label] = {"samples_ns": samples, "includes_host_device_copies": True}
                if label == "cuda_requested":
                    observed = values
            profile_path = Path(gpu.end_profiling())
            profile = json.loads(profile_path.read_text())
            placement = Counter(
                e.get("args", {}).get("provider")
                for e in profile
                if e.get("cat") == "Node" and e.get("args", {}).get("provider")
            )
            parity = []
            for index, (expected, actual) in enumerate(zip(capture.result, observed, strict=True)):
                same_shape = expected.shape == actual.shape
                np.savez_compressed(
                    output / f"{name}-output-{index}.npz", cpu=expected, cuda=actual
                )
                parity.append(
                    {
                        "shape": list(expected.shape),
                        "shape_equal": same_shape,
                        "exact": same_shape and bool(np.array_equal(expected, actual)),
                        "equal_fraction": float(np.mean(expected == actual))
                        if same_shape
                        else None,
                        "max_absolute_difference": float(
                            np.max(np.abs(expected.astype(np.float64) - actual.astype(np.float64)))
                        )
                        if same_shape and expected.size
                        else None,
                        "allclose_rtol_1e-3_atol_1e-4": same_shape
                        and bool(np.allclose(expected, actual, rtol=1e-3, atol=1e-4)),
                    }
                )
            report["models"][name] = {
                "selected_providers": gpu.get_providers(),
                "node_execution_counts": dict(placement),
                "cuda_nodes_observed": placement["CUDAExecutionProvider"] > 0,
                "inputs": [
                    {"name": x.name, "shape": x.shape, "dtype": x.type} for x in gpu.get_inputs()
                ],
                "timings": timings,
                "parity": parity,
                "explicit_session_constructions_per_provider": 1,
                "implicit_fallback_rebuild_possible": "CUDAExecutionProvider"
                not in gpu.get_providers(),
                "scope": "One real frame, FP32, 10 timed repetitions; not dataset accuracy parity",
            }
    finally:
        source.close()
        (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        for directory in dll_directories:
            directory.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "runtime", "libraries", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--cudnn-directory", type=Path)
    parser.add_argument("--strict-fp32", action="store_true")
    args = parser.parse_args()
    run(
        args.config,
        args.runtime,
        args.libraries,
        args.output,
        args.cudnn_directory,
        args.strict_fp32,
    )
