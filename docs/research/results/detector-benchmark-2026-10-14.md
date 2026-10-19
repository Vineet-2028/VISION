# Detector benchmark — 2026-10-14; closure review 2026-10-15

This is measured desktop research, not production qualification. All 26 selected runs completed. No Task007 implementation was started.

## Evidence and reproducibility

Four candidates: YOLO26n, YOLO26s, YOLO11n and official converted RT-DETRv2-R18. Ten native baseline runs cover YOLO 512/640/768 and RT-DETR 640; four ONNX runs, eight synthetic stress runs and four native 640 repeats complete the matrix. Each run evaluates the same 36 images after one cold call and three excluded warmup calls, batch one, one CPU thread, FP32, seed zero.

Checkpoint sources and SHA256 are in `configs/detector-checkpoints.json`. Exact exported hashes, shapes/opset, runtime metadata, cold/warmup timings, all percentile distributions and threshold curves are in the adjacent JSON. The CSV is the flat matrix. The `.dataset.json` is a byte-preserved provenance/annotation manifest, not imagery. Raw predictions remain ignored under `benchmark-results/task006`.

Dataset SHA256: `9b34810576150f24f848f79828055718f5879e3b86aba9768c1c686ce0706f04`. COCO 2017 validation: first six eligible Attribution/Attribution-ShareAlike images per P0 class, deduplicated to 36. All P0 annotations, including ignore/crowd semantics, are retained. There are 212 non-ignored objects: person 98, car 46, bus 18, bicycle 14, truck 14, dog 9, motorcycle 7, train 6. This class-selected subset is biased and too small for safety acceptance. Artist/source/license references are retained; redistribution still needs review.

Hardware: Intel i5-13420H, Windows 11, RTX3050 6GB Laptop (not used), NVIDIA driver 592.27. Python 3.12.10, Torch 2.14.1+cpu, Ultralytics 8.4.177, Transformers 4.57.6, ONNX 1.20.1, ONNX Runtime 1.24.4. Power/thermal state and OS scheduling were not controlled. CUDA installation was declined; GPU/FP16 were not run. `requirements-models.lock` records the observed optional environment.

Original stills have no camera timestamps or calibration. The benchmark uses explicitly synthetic identities and identity-only image geometry; it does not estimate metric distance. Source-video replay preserves real media timestamps through Task005.

## MEASURED LOCALLY — native baseline

Anchor operating point: confidence 0.25, IoU 0.50. This is a comparison point, not a selected production threshold. All eight confidence thresholds and IoU 0.75 results are retained in JSON. Recall is P0 scope, not all 80 COCO classes.

| Candidate/input   | P0 recall | Tiny recall | Small recall | FP/100 images | E2E P95 ms |
| ----------------- | --------: | ----------: | -----------: | ------------: | ---------: |
| rtdetr-v2-r18/640 |    88.68% |      79.17% |       88.89% |       1008.33 |    6725.15 |
| yolo11n/512       |    54.25% |       4.17% |       38.27% |        108.33 |     379.81 |
| yolo11n/640       |    62.26% |      20.83% |       48.15% |        130.56 |     565.61 |
| yolo11n/768       |    64.62% |      29.17% |       50.62% |        130.56 |     680.41 |
| yolo26n/512       |    54.72% |       8.33% |       34.57% |         94.44 |     362.26 |
| yolo26n/640       |    60.85% |      20.83% |       44.44% |        102.78 |     436.63 |
| yolo26n/768       |    63.21% |      20.83% |       45.68% |        105.56 |     574.28 |
| yolo26s/512       |    65.57% |      29.17% |       49.38% |        127.78 |     827.22 |
| yolo26s/640       |    71.70% |      37.50% |       61.73% |        150.00 |     490.57 |
| yolo26s/768       |    74.06% |      41.67% |       70.37% |        155.56 |    1864.74 |

Tiny means normalized box area <0.001 (24 objects); small is [0.001,0.01) (81 objects). These are image-space proxies, not distance. Medium has 66 and large 41 objects.

## Guardian recall and localization at native 640

| Candidate     | Pedestrian | Vehicle | Bicycle | Motorcycle | Mean matched IoU | Bottom-center error |
| ------------- | ---------: | ------: | ------: | ---------: | ---------------: | ------------------: |
| rtdetr-v2-r18 |     93.88% |  83.81% |  78.57% |      0.00% |           0.8117 |              0.0116 |
| yolo11n       |     70.41% |  54.29% |  50.00% |     71.43% |           0.8317 |              0.0148 |
| yolo26n       |     68.37% |  52.38% |  50.00% |     57.14% |           0.8274 |              0.0183 |
| yolo26s       |     79.59% |  62.86% |  57.14% |     71.43% |           0.8424 |              0.0117 |

Vehicle aggregates bicycle, motorcycle, car, bus, truck and train. Bottom-center errors are Euclidean displacement after dividing each axis by image dimensions, on matched boxes only. They do not measure ground-contact accuracy. Per-class TP/FP/FN and macro recall remain visible in JSON. YOLO26s misses 10/14 trucks and 15/24 tiny objects at this operating point.

## Latency and memory — latest native 640 repeat

All values below are milliseconds. Preprocessing includes adapter geometry/color and runtime preprocessing; postprocessing includes output conversion/class mapping/restoration. RT-DETR processor substeps remain combined. YOLO resize/padding/color/tensor/normalization distributions are available separately in JSON. NMS and confidence filtering are combined. Quantiles of stage sums must not be constructed by adding quantiles.

| Candidate     | Stage             |     P50 |     P90 |     P95 |     P99 |
| ------------- | ----------------- | ------: | ------: | ------: | ------: |
| rtdetr-v2-r18 | preprocess_total  |   36.04 |   39.39 |   41.31 |   41.54 |
| rtdetr-v2-r18 | inference         | 5420.31 | 5600.63 | 5631.47 | 5636.24 |
| rtdetr-v2-r18 | postprocess_total |   93.05 |  108.01 |  375.02 |  404.77 |
| rtdetr-v2-r18 | end_to_end        | 5559.27 | 5735.41 | 5957.92 | 6078.48 |
| yolo11n       | preprocess_total  |   21.11 |   24.80 |   26.24 |   33.19 |
| yolo11n       | inference         |  713.97 |  740.22 |  752.98 |  984.54 |
| yolo11n       | postprocess_total |    7.53 |   16.08 |   21.56 |   25.92 |
| yolo11n       | end_to_end        |  753.88 |  770.54 |  792.64 | 1018.29 |
| yolo26n       | preprocess_total  |    3.31 |    4.02 |    5.89 |    6.53 |
| yolo26n       | inference         |   81.69 |  133.93 |  139.46 |  156.55 |
| yolo26n       | postprocess_total |    1.40 |    2.48 |    3.62 |    3.80 |
| yolo26n       | end_to_end        |   87.17 |  138.97 |  145.32 |  165.99 |
| yolo26s       | preprocess_total  |   18.08 |   21.79 |   23.86 |   23.89 |
| yolo26s       | inference         | 1889.13 | 1947.80 | 1961.49 | 1977.56 |
| yolo26s       | postprocess_total |    7.34 |   16.12 |   16.59 |   17.80 |
| yolo26s       | end_to_end        | 1917.82 | 1979.83 | 1991.24 | 2000.80 |

E2E starts from an already decoded original RGB image and ends at DetectionBatch. Disk decode and initial calibration/JVM mapping construction are excluded. Adapter letterbox geometry and restoration are included. Vendor dispatch/housekeeping accounts for differences between E2E and measured stage sums.

| Candidate     | Native file MB | Loaded parameters | Native peak process MB | ONNX file MB | ONNX peak process MB |
| ------------- | -------------: | ----------------: | ---------------------: | -----------: | -------------------: |
| yolo26n       |           5.54 |           2572280 |                 463.95 |         9.88 |               517.64 |
| yolo26s       |          20.42 |          10009784 |                 561.41 |        38.23 |               632.79 |
| yolo11n       |           5.61 |           2624080 |                 453.76 |        10.70 |               514.13 |
| rtdetr-v2-r18 |          80.90 |          20174608 |                 638.45 |        81.02 |               656.03 |

Peak working set covers the whole process, including Python, JVM, imports, decoder, cold calls and warmup; it is not model-only memory. Initial native baseline memory was not recorded and stays null. Parameter counts are after runtime setup, not asserted to be unfused. FLOPs were not measured.

## Runtime parity and export

All four static FP32 exports passed ONNX full structural checking at opset 17, input [1,3,640,640]. YOLO output is [1,84,8400]; RT-DETR outputs [1,300,80] logits and [1,300,4] boxes. RT-DETR legacy-export tracer warnings mean only this fixed shape was validated. CPUExecutionProvider was executed; accelerated providers and mobile operators were not tested.

All 36 frames passed strict native-versus-ONNX class/count association at the 0.05 confidence floor. Allowed score error: 0.001; allowed original-image edge error: 0.5 pixels. No missing/extra detection is tolerated.

| Candidate     | Matched detections | Maximum score error | Maximum edge error px |
| ------------- | -----------------: | ------------------: | --------------------: |
| yolo26n       |                610 |          0.00000209 |              0.000854 |
| yolo26s       |                600 |          0.00000411 |              0.002319 |
| yolo11n       |                724 |          0.00000340 |              0.001312 |
| rtdetr-v2-r18 |               8232 |          0.00004560 |              0.125702 |

Exports retain their original creation-time NOT_YET_TESTED marker; the adjacent comparison JSON supplies the later executed parity verdict. FP32 alone was evaluated. FP16 remains unverified with the unavailable CUDA runtime. INT8 is deliberately deferred until a separate representative calibration set exists.

## Controlled robustness experiments

| Candidate     | Original recall | Synthetic 25% brightness | Synthetic 9px horizontal blur |
| ------------- | --------------: | -----------------------: | ----------------------------: |
| yolo26n       |          60.85% |                   56.13% |                        39.15% |
| yolo26s       |          71.70% |                   63.68% |                        48.11% |
| yolo11n       |          62.26% |                   53.30% |                        38.68% |
| rtdetr-v2-r18 |          88.68% |                   83.02% |                        70.75% |

These are synthetic stress tests, not real low-light, real motion blur or walking-shake validation. Real lighting/scenario/occlusion/truncation labels remain UNKNOWN. The schema supports verified visible/partial/heavy occlusion without inventing labels. A >=5-annotated-person density proxy is reported separately; it is not a human-verified crowd label. No suitable representative multi-minute walking video was available; longevity, realtime drop behavior with real detectors and camera-motion robustness are unverified.

## Selection, licensing and Pareto interpretation

**Provisional research primary: YOLO26s at 640 FP32. Provisional compact fallback: YOLO26n at 640 FP32. Neither is a production-approved winner.** YOLO26s improves P0 and tiny/small recall over nano candidates with less extreme false-positive behavior than RT-DETR at the common anchor threshold. YOLO26n is smaller and supports a speed-oriented follow-up. Native and ONNX both preserve detections; runtime selection remains provisional because latency varies substantially.

RT-DETR is retained as the permissively licensed architecture alternative, not a realtime fallback on this CPU. At confidence 0.60 its recall is 67.92% with 72.22 FP/100, showing why comparing only the default 0.25 would be misleading. YOLO26s at 0.40 has 62.74% recall and 63.89 FP/100. The full curves, not F1 alone, must inform a later operating point.

Observed run-level accuracy/latency frontier: `yolo26s-640-controlled`, `yolo26s-768-controlled`, `rtdetr-v2-r18-640-onnx`, `yolo11n-640-onnx`, `yolo26n-640-repeat`. This excludes neither licensing nor false positives and is not the hard-gated candidate set. No production candidate passes all required gates; product thresholds and legal approval are absent.

**Latency repeatability limitation:** YOLO26s native 640 P95 changed from 490.57 to 1991.24 ms, while YOLO26n changed from 436.63 to 145.32 ms. No controlled thermal/power/frequency or CPU-affinity experiment was performed. Do not conclude that one runtime or resolution is inherently faster from these runs. Retain both measurements and repeat on a controlled target before runtime selection.

Ultralytics code/weights use AGPL-3.0 or enterprise terms according to its stated policy. Closed/proprietary distribution needs review and potentially an enterprise license; ONNX export does not remove obligations. Official RT-DETR code and the converted PekingU model card identify Apache-2.0, with applicable notices/attribution and dependency review still required. See [licensing review](../../perception/DETECTOR_LICENSING.md).

## PUBLISHED EXTERNAL CONTEXT — not local measurements

[Ultralytics YOLO26 documentation](https://docs.ultralytics.com/models/yolo26) publishes COCO validation AP50–95 of 40.9 for nano and 48.6 for small at 640 for the reported one-to-many configuration. Its end-to-end head/speed tables describe different settings. [YOLO11 documentation](https://docs.ultralytics.com/models/yolo11) reports 39.5 for YOLO11n. These full-COCO AP values are not this subset recall, not local timing, and not Android evidence. The [official RT-DETR project](https://github.com/lyuwenyu/RT-DETR) and [pinned converted checkpoint](https://huggingface.co/PekingU/rtdetr_v2_r18vd/tree/1a95089f34a94f1e9db917b053a06c00fdc1c08f) establish provenance, not Guardian qualification.

## Architecture and coverage

Both adapters publish immutable DetectionBatch values with original identity/time, explicit class mapping, confidence, camera-space boxes and model/transform provenance. Vendor tensors/results remain private. YOLO uses actual rounded per-axis letterbox transforms; RT-DETR restores processor coordinates before Task003 inverse mapping. The Task005 scheduler controls independent execution intervals and records overruns. Native calls do not promise hard cancellation. Empty success and failures remain distinct.

P0 classes are PERSON, BICYCLE, MOTORCYCLE, CAR, BUS, TRUCK, TRAIN and DOG. Groups include PEDESTRIAN, VEHICLE and ANIMAL; CYCLIST/STATIC_OBJECT remain reserved rather than inferred. Generic detection does not reliably cover curbs, drains, potholes, stairs, poles, bollards, glass or low branches. Segmentation should describe surfaces/traversability; depth proximity; tracking/flow temporal motion; physics velocity/TTC/CPA. None is implemented by this task.

## Error review, experiments and audit

The adjacent `.errors.json` contains bounded FP/FN, low-IoU and nearest-truth confusion context for native 640 runs, with image references and no copied media. At most 20 examples of each kind per frame are exported. Unmatched P0 predictions are not automatically proven background. The summary contains per-class, size, scenario, density and visibility counts plus confidence/IoU sweeps; no official COCO AP is claimed.

RND-DET-001 through 016 have questions, hypotheses, experiments, metrics, decision criteria and evidence statuses in [the register](../detector-experiments.md). [The adversarial audit](../../perception/TASK006_AUDIT.md) records corrected geometry, wrong-output, runtime-thread and provenance defects. No known CRITICAL/HIGH implementation defect remains from this pass; HIGH production validation/licensing gaps remain open. MEDIUM limits include timing granularity, unstable laptop latency and incomplete dependency vulnerability review. LOW risk is maintenance of pinned vendor extension points.

## Executed verification and verdict

Final full-repository verification: **PASS**, executed 2026-10-15 using `npm run verify` (exit 0). Guardian core: 189 tests and clean build/static analysis; lab: 118 tests, Ruff and strict mypy across 23 source modules; web: 24 tests, lint, strict types and production build; API: 3 tests, formatting, SpotBugs and packaged build. Total: **334 tests**. Security policy passed with the five already reviewed development dependency entries for GHSA-vfj7-8cjw-p6xm still present; this is not zero vulnerabilities. Smoke passed API contracts, production home, eight concurrent health requests and API outage handling. The final log is `benchmark-results/task006/verify-final-retry-2026-10-15.log`. A real-model initialization check also passed after repairing vendor cache-directory creation. Optional model environment `pip check` passed. Four exports and all four same-frame runtime parity comparisons passed. Docker and Android are outside this local model verification; Android was removed by earlier user direction.

TASK 006 COMPLETE: NO — the implemented research baseline and local experiments do not close mandatory representative real-scenario validation. SAFE TO START TASK 007: NO under the requested full Task006 completion gate. Local development can continue; production assistive guidance is not approved. No claim is made that future environment/runtime errors are impossible.

Remaining work is specific: licensed and verified real low-light/occlusion/walking/crowd evaluation data, controlled target-hardware performance evidence, and distribution-specific licensing/acceptance decisions. GPU/FP16 and mobile measurements are unverified; INT8 awaits independent calibration data. None can be replaced by a passing unit test or a synthetic image filter.
