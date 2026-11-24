# GPU execution audit

Windows inventory identifies Intel UHD Graphics and an NVIDIA GeForce RTX 3050
6GB Laptop GPU (driver 32.0.15.9227). The canonical environment has ONNX Runtime
1.24.4 with Azure/CPU providers available; its model adapters explicitly select
CPU. No canonical result is labelled GPU accelerated.

An isolated ONNX Runtime GPU 1.24.4 package and CUDA 12/cuDNN dependencies were
downloaded under the ignored `benchmark-results/v0-rescue/` directory. They do not
replace the application environment. CUDA/cuDNN loading follows the official
[ONNX Runtime CUDA provider documentation](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html).

`tools/rescue_gpu_probe.py` captures actual prepared inputs from the canonical
PicoDet and PIDNet adapters. It records input shapes/dtypes, selected providers,
ten timed repetitions, output comparisons and node execution counts from ORT
profiling. CPU/GPU transfer costs remain included in session timings.

The executed `gpu-probe-02` experiment encountered `CUDNN_BACKEND_API_FAILED`
during the first convolution on both models. ORT fell back to CPU. The report
correctly records **zero CUDA nodes** and CPU-only final selected providers.
Equal output arrays in this experiment are CPU-to-CPU parity, not GPU parity.
The original probe's `load_count_per_provider: 1` counts explicit constructor
calls only; ORT's fallback can internally rebuild the session. The tool now names
that limitation explicitly. It is not evidence of a single internal GPU model load.

The later host-level probe reproduced the cuDNN 9.27 failure. An isolated,
SHA256-verified PyPI `nvidia-cudnn-cu12==9.10.2.21` installation resolved execution.
Default TF32 failed the declared numerical tolerance; `use_tf32=0` passed.
The strict FP32 profile recorded 5,742 detector CUDA node executions and 88 CPU
shape/NMS-related executions, plus 2,255 segmentation CUDA node executions.
These are repeated execution counts, not counts of distinct graph nodes.

Twenty fixed samples spanning 0–570 seconds passed `rtol=1e-3, atol=1e-4` for
both models. Detector selected counts/classes were unchanged at threshold 0.1;
segmentation argmax maps agreed on every sampled pixel. This is numerical parity
on prototype footage, not a dataset accuracy or safety qualification. Raw FP32
arrays are not bit-identical. The dated report records full-run and I/O/FP16 results.

Application CPU defaults remain unchanged. Explicit `device: "cuda:0"` opts in,
disables TF32 and automatic session fallback, and fails if CUDA is unavailable or
initialization selects CPU only. ORT may legitimately assign unsupported individual
operators to CPU; the separate profile makes that placement visible. Model hashes
and FP32 policy are unchanged. No machine-wide driver or environment replacement
was performed.

The probe covers the two configured ONNX models. Alternative detector/semantic
models and Torch depth are not covered by this CUDA result. Depth currently uses
the canonical CPU Torch provider; flow uses CPU OpenCV. No per-frame model load or
per-frame JVM startup was introduced.

## Reproducing the isolated execution

Use the frozen configuration from the desired completed run. The local CUDA
libraries are optional research artifacts, not a new runtime download mechanism.

```powershell
apps/perception-lab/.venv/Scripts/python.exe tools/v0_replay.py --config benchmark-results/v0-rescue/gpu-fp32-config.json --output benchmark-results/v0-rescue/my-gpu-run --mode REALTIME --seconds 600 --ort-runtime benchmark-results/v0-rescue/gpu-runtime --cuda-libraries benchmark-results/v0-rescue/gpu-libraries --cudnn-directory benchmark-results/v0-rescue/cudnn-9.10/nvidia/cudnn/bin
```

`tools/rescue_gpu_validate.py` reproduces the 20-frame parity study, reusable GPU
input-buffer experiment and isolated FP16 screening. NMS has dynamic output extent;
I/O binding must refresh output bindings between calls. The first binding trial
failed when it retained a prior output allocation; its failed report is preserved.
No experimental converted checkpoint replaces a reviewed application model.
