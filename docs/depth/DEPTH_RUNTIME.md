# Depth runtime

Explicit checkpoint acquisition (network only during this command):

```powershell
apps/perception-lab/.venv/Scripts/python.exe tools/download_depth.py
```

This verifies pinned hashes and preserves unexpected existing files. It downloads
only model artifacts; inference remains offline. Install the existing optional
model lockfile using the perception-lab README before using real providers.

`configs/perception-lab.depth.example.json` is a portable configuration template.
Replace its video/calibration paths with a matching local recording and calibration
before replay. The bundled 8x6 synthetic calibration is test-only and is not a real
camera calibration. Paths resolve relative to the configuration file. The template
uses offline replay so it does not imply achieved realtime cadence.

The realtime decoder now catches up in bounded 32-frame batches, extending up to
1,024 admissions only while lateness decreases. A slower-than-source decoder yields
after a batch. This prevents the old fixed batch limit from perpetually lagging a
slow inference. It does not make inference fast or promise live deadlines.

IMPLEMENTED: synthetic provider and local Transformers Depth Anything V2 Small relative/outdoor metric providers. Configure depth.provider, local weights, three SHA256 values, input_size (266/392/518), threads, and an independent intervals_ns.depth.

Weights must be model.safetensors. Weight/config/processor hashes are verified before loading. No remote custom code or automatic model download is used in inference. Python network denial and Hugging Face offline/telemetry flags apply before vendor imports. Optional runtime dependencies already exist in requirements-models.lock; no new framework is required.

The processor resizes preserving aspect ratio with a multiple-of-14 constraint. Padded processor configurations are rejected. The actual output dimensions determine the Java resize mapping. Output is not expanded to the camera resolution.

The model is loaded once and runs batch=1 CPU FP32. Timing separates preprocessing, runtime and map conversion; pipeline metrics separate depth, object sampling and result age. Thread count is configured, not chosen per frame. Model loading and inference remain synchronous and cannot be preempted by a Python deadline; cancellation is observed between stages.

Native here means Transformers PyTorch, not original upstream OpenCV preprocessing. Original-upstream parity is not established. A one-frame fixed-shape relative-model ONNX export passed numerical tolerance; broad parity and a selectable ONNX replay provider remain unimplemented. No quantization, GPU or mobile throughput claim. Relative output is larger-is-nearer, metric output is Z in meters with a configured 80 m ceiling.

Run a local configured replay:

```powershell
apps/perception-lab/.venv/Scripts/python.exe -m perception_lab.cli replay --config benchmark-results/task008/replay-2hz.config.json --headless
```

Private example configurations and downloaded weights are ignored; a clean installation must acquire the exact reviewed artifacts listed in the model BOM.
