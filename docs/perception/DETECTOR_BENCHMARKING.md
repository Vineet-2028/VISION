# Detector benchmarking

The benchmark is opt-in and excluded from normal CI. No benchmark command downloads weights or media. Use Python 3.12 and build guardian-core first.

```powershell
npm run check:core
$python = ".\apps\perception-lab\.venv\Scripts\python.exe"
& $python -m pip install -r apps/perception-lab/requirements-models.txt
# After acquiring the official annotation archive in datasets/raw/coco2017:
& $python tools/curate_coco.py
$weights = "benchmark-results/task006/models/yolo26n.pt"
$hash = (Get-FileHash -LiteralPath $weights -Algorithm SHA256).Hash.ToLowerInvariant()
& $python -m perception_lab.detector_benchmark --dataset datasets/raw/coco2017/sentinel-subset.json --weights $weights --sha256 $hash --output benchmark-results/task006/yolo26n-640.json --size 640 --warmup 3 --threads 1
```

Only compute the hash after trusted acquisition; comparing a malicious file against its own hash does not establish trust. Output paths must be new, so evidence is not overwritten. RT-DETR uses --runtime rtdetr and a local model.safetensors with sibling config.json/preprocessor_config.json. Sizes 512/640/768 are diagnostic experiments; the official RT-DETR processor recommends 640.

Dataset policy: first six sorted eligible COCO validation image IDs per P0 class, deduplicated, with all P0 annotations retained. The resulting 36-image subset is deliberately class-selected and biased. It is suitable for regression and initial comparison, not a representative Guardian validation or held-out production acceptance set. Dataset/model hashes, IDs, runtime, configuration and platform are recorded. Unknown scene/lighting/occlusion fields stay unknown.

Every run has batch size one, one cold call, configurable additional warmup excluded from steady statistics, and controlled CPU threads. P50/P90/P95/P99 use nearest-rank statistics across the complete measured image count. GPU paths synchronize before measured boundaries. Disk read/decode and per-image identity geometry construction are excluded and explicitly disclosed. YOLO separately times color conversion, resize, padding, tensor transfer and normalization. NMS/filtering remain combined in vendor postprocessing; class conversion and inverse geometry remain combined in coordinate restoration. RT-DETR processor stages remain combined and it has no NMS step. Do not add percentile values to estimate a percentile of their sum.

JSON contains predictions and bounded-per-image error references without copying media. Runs fail nonzero on exceptions; error reports never masquerade as zero detections. Vendor error strings/private paths are omitted. OOM does not terminate the invoking comparison script if it checks each run's exit status and continues.

Missing evidence remains null/unmeasured. New runs record process RSS and Windows peak working set when psutil is available; this includes Python, JVM, decoder, runtime, cold calls and warmup, not just model memory. Synthetic darkening multiplies pixels by 0.25; synthetic blur uses a nine-pixel horizontal box kernel with edge padding. These transformations occur outside inference timing and never establish real low-light or camera-motion robustness. INT8 requires a separate representative calibration set; do not calibrate against this evaluation subset.

Export is explicit: `python tools/export_detectors.py --weights <trusted-local-file> --sha256 <trusted-hash>` (add `--runtime rtdetr` for RT-DETR). Successful ONNX checking is only structural validation. Run the exported checkpoint through the same benchmark and compare outputs before accepting it. Detection parity requires matching classes/counts, score error at most 0.001 and every original-image box-edge error at most 0.5 pixels. A missing or extra detection fails strict parity, including threshold-boundary differences.

`python tools/summarize_detectors.py --output docs/research/results/detector-benchmark-2026-10-14.json` produces the JSON/CSV matrix, confidence sweeps, parity and bounded error-review JSON from explicitly named controlled runs. It recomputes diagnostics from retained predictions without changing measured latency. It rejects dataset/order mismatches. Error examples are limited to 20 per kind per frame for the native 640 runs; no source pixels are copied. `NO_P0_MATCH_AT_IOU_0_5` does not prove a detection is background: this dataset labels only P0 categories for this evaluation.
