"""Local sampled CPU/CUDA parity and copy-inclusive I/O binding experiment."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from time import perf_counter_ns

from rescue_runtime import activate_onnx


def run(args):
    import numpy as np

    ort, handles = activate_onnx(args.runtime, args.libraries, args.cudnn_directory)
    from perception_lab.config import Calibration, LabConfig, read_json
    from perception_lab.edge_runtime import PicoDetDetector
    from perception_lab.geometry import CoreGeometry
    from perception_lab.preprocessing import BasicPreprocessor
    from perception_lab.semantic_runtime import OnnxSemanticSegmenter
    from perception_lab.sources import VideoFileSource

    args.output.mkdir(parents=True, exist_ok=False)
    config = LabConfig.model_validate(read_json(args.config))
    base = args.config.resolve().parent
    geometry = CoreGeometry(Calibration.model_validate(read_json(base / config.calibration)))
    source = VideoFileSource(base / config.input, config.source_id, config.max_pixels)
    report = {
        "scope": "20 fixed samples at 30-second intervals; numerical, not accuracy parity",
        "models": {},
        "frames": [],
        "io_binding": {},
        "graph_cache": {},
        "execution_profiles": {},
        "runtime": ort.__version__,
        "status": "RUNNING",
    }

    class Capture:
        def __init__(self, session):
            self.session = session

        def run(self, names, feed):
            self.feed = feed
            self.result = self.session.run(names, feed)
            return self.result

        def __getattr__(self, name):
            return getattr(self.session, name)

    try:
        detector, semantic = config.detector, config.segmentation
        assert detector
        adapters = {
            "detector": (
                PicoDetDetector(
                    base / detector.weights, detector.sha256, confidence=detector.confidence
                ),
                "detect",
                base / detector.weights,
            ),
        }
        if semantic is not None:
            adapters["segmentation"] = (
                OnnxSemanticSegmenter(
                    semantic.model_copy(update={"device": "cpu"}), base, "parity"
                ),
                "segment",
                base / semantic.weights,
            )
        sessions = {}
        for name, (adapter, _, weights) in adapters.items():
            options = ort.SessionOptions()
            options.intra_op_num_threads = options.inter_op_num_threads = 1
            gpu = ort.InferenceSession(
                str(weights),
                options,
                providers=[("CUDAExecutionProvider", {"use_tf32": "0"}), "CPUExecutionProvider"],
            )
            gpu.disable_fallback()
            if "CUDAExecutionProvider" not in gpu.get_providers():
                raise RuntimeError("CUDA initialization failed")
            adapter.session = Capture(adapter.session)
            sessions[name] = gpu
            report["models"][name] = {"providers": gpu.get_providers(), "samples": []}
        next_ns = 0
        source.realtime_minimum_ns = lambda: next_ns
        for frame in source:
            if frame.identity.observation_ns >= 600_000_000_000:
                break
            image = BasicPreprocessor(geometry, config.preprocess).prepare(frame)
            report["frames"].append(frame.identity.observation_ns)
            for name, (adapter, method, _) in adapters.items():
                getattr(adapter, method)(image, frame.identity)
                capture = adapter.session
                actual = sessions[name].run(None, capture.feed)
                comparisons = []
                for expected, observed in zip(capture.result, actual, strict=True):
                    comparisons.append(
                        {
                            "same_shape": expected.shape == observed.shape,
                            "allclose": expected.shape == observed.shape
                            and bool(np.allclose(expected, observed, rtol=1e-3, atol=1e-4)),
                            "max_absolute_difference": float(np.max(np.abs(expected - observed))),
                        }
                    )
                if name == "segmentation":
                    detail = {
                        "argmax_agreement": float(
                            np.mean(capture.result[0].argmax(axis=1) == actual[0].argmax(axis=1))
                        )
                    }
                else:
                    cpu_rows = capture.result[0][capture.result[0][:, 1] >= detector.confidence]
                    gpu_rows = actual[0][actual[0][:, 1] >= detector.confidence]
                    detail = {
                        "selected_count_cpu": len(cpu_rows),
                        "selected_count_gpu": len(gpu_rows),
                        "selected_classes_equal": cpu_rows.shape == gpu_rows.shape
                        and bool(np.array_equal(cpu_rows[:, 0], gpu_rows[:, 0])),
                    }
                report["models"][name]["samples"].append(
                    {"source_ns": frame.identity.observation_ns, "outputs": comparisons, **detail}
                )
            next_ns += 30_000_000_000
            if len(report["frames"]) == 20:
                break
        report["fp32_parity_passed"] = len(report["frames"]) == 20 and all(
            all(output["allclose"] for output in sample["outputs"])
            and sample.get("selected_classes_equal", True)
            and sample.get("selected_count_cpu") == sample.get("selected_count_gpu")
            and sample.get("argmax_agreement", 1.0) == 1.0
            for model in report["models"].values()
            for sample in model["samples"]
        )
        if not report["fp32_parity_passed"]:
            raise RuntimeError("FP32 parity or full 20-frame sample gate failed")
        for name, (adapter, _, _) in adapters.items():
            session, feed = sessions[name], adapter.session.feed
            binding = session.io_binding()
            inputs = {
                key: ort.OrtValue.ortvalue_from_numpy(value, "cuda", 0)
                for key, value in feed.items()
            }
            for key, value in inputs.items():
                binding.bind_ortvalue_input(key, value)
            # Dynamic NMS output cannot use a fixed-size reusable output allocation.
            for output in session.get_outputs():
                binding.bind_output(output.name, "cuda")
            timings = {}
            bound_outputs = None
            for strategy in ("session_run", "binding_reused_input"):
                samples = []
                for _ in range(21):
                    start = perf_counter_ns()
                    if strategy == "session_run":
                        expected = session.run(None, feed)
                    else:
                        for key, value in inputs.items():
                            value.update_inplace(feed[key])
                        # NMS changes output extent; do not retain a prior bound allocation.
                        binding.clear_binding_outputs()
                        for output in session.get_outputs():
                            binding.bind_output(output.name, "cuda")
                        binding.synchronize_inputs()
                        session.run_with_iobinding(binding)
                        binding.synchronize_outputs()
                        bound_outputs = binding.copy_outputs_to_cpu()
                    samples.append(perf_counter_ns() - start)
                timings[strategy] = samples[1:]
            report["io_binding"][name] = {
                "samples_ns": timings,
                "includes_input_upload_and_output_download": True,
                "parity": all(
                    np.allclose(a, b, rtol=1e-3, atol=1e-4)
                    for a, b in zip(expected, bound_outputs, strict=True)
                ),
            }
            # Separate profiling session keeps profiler overhead out of binding timings.
            profile_options = ort.SessionOptions()
            profile_options.intra_op_num_threads = profile_options.inter_op_num_threads = 1
            profile_options.enable_profiling = True
            profile_options.profile_file_prefix = str(args.output / (name + "-execution"))
            profiled = ort.InferenceSession(
                str(adapters[name][2]),
                profile_options,
                providers=[("CUDAExecutionProvider", {"use_tf32": "0"}), "CPUExecutionProvider"],
            )
            profiled.disable_fallback()
            profiled.run(None, feed)
            profile_path = Path(profiled.end_profiling())
            nodes = Counter(
                event.get("args", {}).get("provider")
                for event in json.loads(profile_path.read_text())
                if event.get("cat") == "Node" and event.get("args", {}).get("provider")
            )
            report["execution_profiles"][name] = dict(nodes)
            if not nodes["CUDAExecutionProvider"]:
                raise RuntimeError("No actual CUDA node executions recorded")
            del profiled
            cache_path = args.output / (name + "-cuda-optimized.onnx")
            cache_options = ort.SessionOptions()
            cache_options.intra_op_num_threads = cache_options.inter_op_num_threads = 1
            cache_options.optimized_model_filepath = str(cache_path)
            cache_start = perf_counter_ns()
            cached = ort.InferenceSession(
                str(adapters[name][2]),
                cache_options,
                providers=[("CUDAExecutionProvider", {"use_tf32": "0"}), "CPUExecutionProvider"],
            )
            cache_build_ns = perf_counter_ns() - cache_start
            cached.disable_fallback()
            cached.run(None, feed)
            del cached
            cache_options.optimized_model_filepath = ""
            cache_start = perf_counter_ns()
            cached = ort.InferenceSession(
                str(cache_path),
                cache_options,
                providers=[("CUDAExecutionProvider", {"use_tf32": "0"}), "CPUExecutionProvider"],
            )
            cache_load_ns = perf_counter_ns() - cache_start
            cached.disable_fallback()
            cached_samples = []
            for _ in range(21):
                tick = perf_counter_ns()
                cached_output = cached.run(None, feed)
                cached_samples.append(perf_counter_ns() - tick)
            with cache_path.open("rb") as cache_file:
                cache_hash = hashlib.file_digest(cache_file, "sha256").hexdigest()
            report["graph_cache"][name] = {
                "build_and_serialize_ns": cache_build_ns,
                "load_ns": cache_load_ns,
                "steady_state_samples_ns": cached_samples[1:],
                "sha256": cache_hash,
                "runtime": ort.__version__,
                "provider": "CUDAExecutionProvider",
                "tf32": False,
                "threads": 1,
                "target_scope": "THIS_HOST_AND_PROVIDER_ONLY; NOT_PORTABLE",
                "parity": all(
                    a.shape == b.shape and np.allclose(a, b, rtol=1e-3, atol=1e-4)
                    for a, b in zip(expected, cached_output, strict=True)
                ),
                "adopted": False,
            }
            del cached
        # Converted artifacts remain isolated; application hash pins and FP32 policy stay intact.
        import onnx
        from onnxruntime.transformers.float16 import convert_float_to_float16

        report["fp16"] = {}
        for name, (adapter, _, weights) in adapters.items():
            try:
                converted = convert_float_to_float16(onnx.load(str(weights)), keep_io_types=True)
                target = args.output / (name + "-experimental-fp16.onnx")
                onnx.save(converted, str(target))
                half = ort.InferenceSession(
                    str(target),
                    providers=[
                        ("CUDAExecutionProvider", {"use_tf32": "0"}),
                        "CPUExecutionProvider",
                    ],
                )
                half.disable_fallback()
                if "CUDAExecutionProvider" not in half.get_providers():
                    raise RuntimeError("FP16 CUDA initialization failed")
                feed = adapter.session.feed
                samples = []
                for _ in range(11):
                    start = perf_counter_ns()
                    observed = half.run(None, feed)
                    samples.append(perf_counter_ns() - start)
                report["fp16"][name] = {
                    "scope": "Last sampled frame, strict FP32 tolerance screening only",
                    "samples_ns": samples[1:],
                    "allclose_rtol_1e-3_atol_1e-4": all(
                        a.shape == b.shape and np.allclose(a, b, rtol=1e-3, atol=1e-4)
                        for a, b in zip(adapter.session.result, observed, strict=True)
                    ),
                    "adopted": False,
                }
            except Exception as error:
                report["fp16"][name] = {"error_type": type(error).__name__, "adopted": False}
        report["status"] = "COMPLETE_EXPERIMENT_REQUIRES_ADOPTION_REVIEW"
    except BaseException as error:
        report.update(status="FAILED", error_type=type(error).__name__)
        raise
    finally:
        source.close()
        (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        for handle in handles:
            handle.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "runtime", "libraries", "cudnn-directory", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    run(parser.parse_args())
