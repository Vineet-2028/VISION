# Detector qualification — Task 006B

Measurements begun 2026-10-15; closure review 2026-10-16. **TASK 006 COMPLETE: NO. SAFE TO START TASK 007: NO.**

The software and public diagnostic analysis progressed. Approved real-world media, reviewed annotations and representative sustained-video evidence are still missing. This report does not substitute test success for qualification.

## A–C. Dataset created, statistics and annotation quality

No Sentinel real-world evaluation dataset has been acquired: **0 sequences, 0 frames, 0 objects**. The existing 36 attributed COCO images and 212 non-ignored P0 instances remain `DIAGNOSTIC_PUBLIC_SUBSET`. They are deliberately class-selected stills, not representative walking samples. Dataset SHA256: `9b34810576150f24f848f79828055718f5879e3b86aba9768c1c686ce0706f04`.

Class denominators: PERSON 98, BICYCLE 14, MOTORCYCLE 7, CAR 46, BUS 18, TRUCK 14, TRAIN 6, DOG 9. The tiny class has 24 objects, small 81, medium 66, large 41. Adjacent public JSON/CSV/SVG preserve empirical curves; runtime JSON preserves all 14 new runs, provenance and parity. Raw predictions remain ignored locally.

Added deterministic PTS frame export, COCO import, version-one manifests, hashing, split/duplicate checks and annotation audits. Draft/imported annotations cannot pass validation until reviewed. Structural validation does not prove semantic correctness. [Workflow and source review](../../perception/REAL_WORLD_EVALUATION.md).

The user chose approved public-dataset access. [JRDB request](../dataset-access-request.md) is prepared but **not sent**: sender identity/affiliation are missing. Official JRDB registration requires institutional details and supervisor; independent access must be clarified. Ego4D requires the user-executed agreement and publisher credentials. No approvals or accounts are invented.

## D. PUBLIC DIAGNOSTIC RESULTS

All four prior confidence 0.25 / IoU 0.50 metrics reproduced from saved predictions and from new 0.01-floor inference. New runs: four native, four ONNX, four native repeats at 640, plus YOLO26s and RT-DETR native 768. Batch one, FP32, requested/effective runtime threads one, five excluded warmup calls plus one excluded cold call.

| Candidate     | Recall at 0.25 |  FP/100 |
| ------------- | -------------: | ------: |
| yolo26n       |         60.85% |  102.78 |
| yolo26s       |         71.70% |  150.00 |
| yolo11n       |         62.26% |  130.56 |
| rtdetr-v2-r18 |         88.68% | 1008.33 |

## E. SENTINEL REAL-WORLD RESULTS

Unavailable; all real-world accuracy, scenario, localization, latency, result-age and memory cells are N/A. The adjacent `.real-world.csv` and `.real-world.json` retain explicit null/unavailable fields for all candidates. Public and real-world results are never pooled. No combined number is reported.

## F. Fixed-FP comparison — PUBLIC_DIAGNOSTIC

Maximum recall under each FP cap, selecting an observed 0.01-spaced threshold, IoU 0.50. With 36 frames, one FP changes the rate by 2.78. Budgets correspond to at most 9, 18 and 36 FP; equality may be unattainable. **All thresholds were selected post-hoc on this same dataset, not independently calibrated.** VEHICLE means CAR/BUS/TRUCK/TRAIN (84 objects); two-wheelers are separate. The older report used a broader vehicle grouping.

| Model         | FP cap | Threshold | Actual FP/100 | P0 recall | Person | Bicycle | Motorcycle | Vehicle |
| ------------- | -----: | --------: | ------------: | --------: | -----: | ------: | ---------: | ------: |
| yolo26n       |     25 |      0.51 |         25.00 |    41.51% | 46.94% |  35.71% |     57.14% |  30.95% |
| yolo26n       |     50 |      0.39 |         47.22 |    53.30% | 63.27% |  35.71% |     57.14% |  41.67% |
| yolo26n       |    100 |      0.26 |         94.44 |    59.91% | 68.37% |  50.00% |     57.14% |  50.00% |
| yolo26s       |     25 |      0.66 |         19.44 |    45.28% | 52.04% |  35.71% |     42.86% |  36.90% |
| yolo26s       |     50 |      0.44 |         50.00 |    59.91% | 67.35% |  42.86% |     71.43% |  51.19% |
| yolo26s       |    100 |      0.36 |         86.11 |    64.62% | 70.41% |  50.00% |     71.43% |  57.14% |
| yolo11n       |     25 |      0.51 |         25.00 |    42.92% | 51.02% |  35.71% |     57.14% |  30.95% |
| yolo11n       |     50 |      0.43 |         47.22 |    48.58% | 57.14% |  35.71% |     71.43% |  36.90% |
| yolo11n       |    100 |      0.29 |         91.67 |    58.49% | 67.35% |  50.00% |     71.43% |  47.62% |
| rtdetr-v2-r18 |     25 |      0.83 |         22.22 |    41.04% | 44.90% |  42.86% |      0.00% |  35.71% |
| rtdetr-v2-r18 |     50 |      0.73 |         47.22 |    52.36% | 60.20% |  57.14% |      0.00% |  44.05% |
| rtdetr-v2-r18 |    100 |      0.53 |         97.22 |    70.28% | 78.57% |  57.14% |      0.00% |  67.86% |

## G. Fixed-precision comparison — PUBLIC_DIAGNOSTIC

| Model         | Target | Threshold | Actual precision | Actual recall | FP/100 |
| ------------- | -----: | --------: | ---------------: | ------------: | -----: |
| yolo26n       |    80% |      0.28 |           81.29% |        59.43% |  80.56 |
| yolo26n       |    90% |      0.51 |           90.72% |        41.51% |  25.00 |
| yolo26n       |    95% |      0.68 |           95.31% |        28.77% |   8.33 |
| yolo26s       |    80% |      0.36 |           81.55% |        64.62% |  86.11 |
| yolo26s       |    90% |      0.50 |           90.44% |        58.02% |  36.11 |
| yolo26s       |    95% |      0.80 |           96.88% |        29.25% |   5.56 |
| yolo11n       |    80% |      0.32 |           80.71% |        53.30% |  75.00 |
| yolo11n       |    90% |      0.50 |           90.38% |        44.34% |  27.78 |
| yolo11n       |    95% |      0.71 |           95.31% |        28.77% |   8.33 |
| rtdetr-v2-r18 |    80% |      0.52 |           80.21% |        70.75% | 102.78 |
| rtdetr-v2-r18 |    90% |      0.81 |           90.38% |        44.34% |  27.78 |
| rtdetr-v2-r18 |    95% |      0.93 |           96.77% |        14.15% |   2.78 |

## H. Fixed-recall comparison — PUBLIC_DIAGNOSTIC

| Model         | Target | Threshold | Actual precision | Actual recall |  FP/100 |
| ------------- | -----: | --------: | ---------------: | ------------: | ------: |
| yolo26n       |    80% |      0.07 |           46.58% |        80.19% |  541.67 |
| yolo26n       |    85% |      0.01 |           16.61% |        85.85% | 2538.89 |
| yolo26n       |    90% |       N/A |              N/A |           N/A |     N/A |
| yolo26n       |    95% |       N/A |              N/A |           N/A |     N/A |
| yolo26s       |    80% |      0.10 |           57.58% |        80.66% |  350.00 |
| yolo26s       |    85% |      0.06 |           48.27% |        85.38% |  538.89 |
| yolo26s       |    90% |      0.01 |           21.28% |        91.04% | 1983.33 |
| yolo26s       |    95% |       N/A |              N/A |           N/A |     N/A |
| yolo11n       |    80% |      0.02 |           21.83% |        81.13% | 1711.11 |
| yolo11n       |    85% |      0.01 |           15.71% |        85.38% | 2697.22 |
| yolo11n       |    90% |       N/A |              N/A |           N/A |     N/A |
| yolo11n       |    95% |       N/A |              N/A |           N/A |     N/A |
| rtdetr-v2-r18 |    80% |      0.34 |           51.67% |        80.19% |  441.67 |
| rtdetr-v2-r18 |    85% |      0.29 |           42.72% |        85.85% |  677.78 |
| rtdetr-v2-r18 |    90% |      0.22 |           28.01% |        90.09% | 1363.89 |
| rtdetr-v2-r18 |    95% |       N/A |              N/A |           N/A |     N/A |

PR curves include every 0.01 threshold through 0.95, overall and by requested group. No missing 0.01–0.04 scores are inferred from older predictions. Unavailable targets remain unavailable. Curves are empirical; plot segments do not imply an achievable interpolated threshold. Model output limits remain 300, so this is a pipeline operating curve, not unrestricted raw-logit COCO AP.

## I. Image-size proxy and resolution results

Normalized area/image area: tiny <0.001, small [0.001,0.01), medium [0.01,0.1), large >=0.1. These are image-size proxies, never meters. Confidence 0.25 / IoU 0.50; public diagnostic only.

| Candidate/resolution | P0 recall | Tiny matched/24 | Small matched/81 |
| -------------------- | --------: | --------------: | ---------------: |
| yolo26n-640          |    60.85% |            5/24 |            36/81 |
| yolo26s-640          |    71.70% |            9/24 |            50/81 |
| yolo11n-640          |    62.26% |            5/24 |            39/81 |
| rtdetr-v2-r18-640    |    88.68% |           19/24 |            72/81 |
| yolo26s-768          |    74.06% |           10/24 |            57/81 |
| rtdetr-v2-r18-768    |    87.26% |           18/24 |            70/81 |

YOLO26s improves tiny/small counts at 768; RT-DETR does not on this subset. Native 768 P95 was 596.83 ms / 9155.98 ms respectively. Unstable CPU rounds prohibit a precise resolution cost estimate. These are the strongest two by public recall, not real-world winners.

## J–M. ROBUSTNESS

Real occlusion, camera-motion, low-light and blur results: **N/A**, with no verified real-world slice denominators. Public occlusion/lighting labels remain UNKNOWN. Earlier synthetic darkening and horizontal blur are preserved separately in the previous report and are not relabeled as real scenarios. No distance estimate or wearer safety claim follows.

## N. Localization and ERROR ANALYSIS

The `.accuracy.json` records per-group bottom-center errors and matched counts, mean IoU and size/scenario denominators. Errors are normalized per axis, computed on matched detections only; misses are not hidden in these means. The `.errors.json` contains at most 20 high-confidence FP, priority FN and low-IoU matches per candidate. Bicycle/motorcycle/person/vehicles are prioritized for FN review. Context labels are **automatic, not human-confirmed failure causes**; small-image size does not prove why a detector missed an object. No new video/image review set was represented as completed.

## O. Detailed RUNTIME RESULTS

New native/ONNX round-one P95 milliseconds at 640 and floor 0.01. All detailed P50/P90/P95/P99 stages, phases, process peak memory, hashes, source-code snapshots and runtime settings remain in `.runtime.json`. Whole-process memory includes Python/JVM/runtime/imports; it is not model-only.

| Candidate/runtime        | Preprocess | Inference | Postprocess | E2E P95 | E2E P99 |
| ------------------------ | ---------: | --------: | ----------: | ------: | ------: |
| rtdetr-v2-r18-640-native |      43.01 |   5674.29 |      384.36 | 5799.09 | 5825.29 |
| rtdetr-v2-r18-640-onnx   |      47.96 |   4759.09 |      345.95 | 4903.27 | 4934.74 |
| yolo11n-640-native       |      24.68 |    729.36 |       54.72 |  779.97 | 1049.22 |
| yolo11n-640-onnx         |      20.57 |    602.13 |       61.44 |  677.10 |  899.50 |
| yolo26n-640-native       |      14.03 |    466.37 |       30.99 |  533.81 |  652.99 |
| yolo26n-640-onnx         |      21.39 |    507.68 |       53.45 |  560.44 |  794.01 |
| yolo26s-640-native       |      23.38 |   2035.09 |       34.56 | 2067.36 | 2512.92 |
| yolo26s-640-onnx         |      19.82 |   1676.97 |       39.55 | 1731.91 | 1923.92 |

Loaded RGB image to DetectionBatch includes adapter geometry, color, vendor inference/postprocessing, output transfer, class mapping, restoration/detection creation and batch creation. File decode and initial JVM mapping setup are excluded. YOLO has resize/pad/tensor/normalization and NMS-with-confidence-filter substages. RT-DETR processor preprocessing remains combined; its confidence filtering and box scaling are also combined. Pure NMS, class filtering and GPU synchronization are not falsely assigned independent timings where unavailable. Thus the fully separated A–L timing requirement remains **PARTIAL**. Do not add substage percentiles to obtain total latency.

Benchmark outer timing always included batch creation; the adapter-only timer now includes it too. Metric/manifest/report changes after inference do not alter stored predictions; recorded source hashes identify each executed version. Historical RT-DETR configuration retains a generic nms_iou field, but runtime_metadata explicitly says NMS_FREE; it was not applied. Future reports set that inapplicable field to null.

## P. CPU stability

| Model         | Round 1 P95 ms | Round 2 P95 ms | Sample CV |
| ------------- | -------------: | -------------: | --------: |
| yolo26n       |         533.81 |        1073.28 |     47.5% |
| yolo26s       |        2067.36 |         441.23 |     91.7% |
| yolo11n       |         779.97 |        1007.96 |     18.0% |
| rtdetr-v2-r18 |        5799.09 |        6446.06 |      7.5% |

CV = sample standard deviation / mean of the two observed P95 values. Two rounds are insufficient for stable confidence intervals. OMP/MKL/OpenBLAS and runtime thread counts were set to one, seed zero, cold/warmup excluded, GC enabled. Windows power plan was observed as Balanced; it was not changed. Frequency snapshots vary and are not a frequency trace. Background activity/thermal state/OneDrive were not isolated, and sandbox process counts do not describe all host processes. No causal diagnosis is established.

## Q–S. GPU, ONNX CUDA and FP16

Fresh capability check: Torch CUDA unavailable; ONNX providers are AzureExecutionProvider and CPUExecutionProvider, with no CUDAExecutionProvider. All measured execution used CPU. GPU/FP16 are N/A. Prior CUDA-installation refusal remains respected. INT8 is deferred because no independent representative calibration dataset exists.

## T–U. Long-video stability and realtime result age

Representative multi-minute video and 5/10/15 Hz real-model replay are **NOT EXECUTED**: approved suitable video is unavailable. No synthetic or repeated still-image sequence is substituted. Replay age instrumentation and its offset-clock regression test are implemented; no real-video P50/P95/P99 age, achieved detector Hz or sustained-memory claim exists. See the local workflow for exact clock semantics and recent-window percentile scope.

## V. Real-world Pareto frontier

Unavailable without real-world recall/FP/latency. Tested 3D non-dominance support maximizes recall and minimizes FP burden and latency; licensing is deliberately separate. Unstable laptop data and post-hoc public operating points do not establish a product frontier.

## W. Licensing

Official upstream sources rechecked 2026-10-15: [Ultralytics](https://www.ultralytics.com/license), [RT-DETR Apache-2.0](https://github.com/lyuwenyu/RT-DETR/blob/main/LICENSE), [PekingU checkpoint](https://huggingface.co/PekingU/rtdetr_v2_r18vd). YOLO research status REVIEW_REQUIRED; private R&D is not automatically exempt. Proprietary deployment requires a documented applicable compliance route or enterprise terms. RT-DETR upstream license identification is CLEAR, while complete product distribution/dependency review remains REVIEW_REQUIRED. No legal approval is asserted.

All four native/ONNX pairs passed 36-image parity at the 0.01 floor, tolerances 0.001 score and 0.5 original-image pixels, with no missing/extra/out-of-tolerance detections. Static CPU FP32 export is tested; mobile export/device execution remains N/A.

## X–Z. PROVISIONAL DECISION

**Primary: NOT SELECTED. Fallback: NOT SELECTED.** YOLO26s has the best diagnostic recall under the 25 and 50 FP/100 caps; RT-DETR wins at the 100 cap. No candidate satisfies the requested real-world and practical-runtime evidence gate. The historical YOLO26s preference is not automatically promoted into Task007.

## AA. Pretrained-model sufficiency

Insufficient evidence to decide sufficiency for Guardian. Continue pretrained evaluation after data approval; do not train now. Tiny objects and some minority classes warrant investigation, not automatic fine-tuning.

## AB. Detector scope limits

| Hazard                          | Future owner                                                 |
| ------------------------------- | ------------------------------------------------------------ |
| Walkable surface                | SEGMENTATION + GROUND GEOMETRY                               |
| Curb, step down, open drain     | DEPTH + GROUND GEOMETRY, with specialized evidence if needed |
| Pothole                         | SPECIALIZED MODEL + GROUND GEOMETRY                          |
| Small pole outside the taxonomy | SPECIALIZED MODEL / SEGMENTATION                             |

No future subsystem is implemented in this task.

## AC. Tests

Analytical tests cover operating points, unreachable targets, confidence-prefix equivalence, PR envelope boundaries, three-dimensional Pareto behavior, dataset hashes/boxes/duplicates/split leakage, sampling, COCO category mapping, source identity, GPU synchronization dispatch and replay-clock age. Real-model checks remain outside generic CI. Final full verification is recorded below once executed.

## AD. Adversarial audit

Read-only pre-task inspection preceded changes; metrics reproduced exactly. [Audit](../../perception/TASK006B_AUDIT.md) distinguishes repaired implementation/reporting issues from outstanding qualification inputs. No confirmed unresolved CRITICAL implementation finding. HIGH: real-world qualification and licensing decisions remain open. MEDIUM: runtime variability, combined RT-DETR timing, annotation semantic review, incomplete vulnerability review. LOW: pinned vendor-maintenance burden.

## AE. Full repository verification

**PASS � `npm run verify`, exit 0, 2026-10-16.** Guardian core 189 tests; perception lab 142; web 24; API 3: **358 tests total**. Formatting, Ruff, strict mypy, ESLint, strict TypeScript, SpotBugs, web/API builds, security policy and production smoke checks passed. `pip check` also passed. Log: `benchmark-results/task006b/verify-final-2026-10-16.log`. The security policy retains five development-dependency entries for GHSA-vfj7-8cjw-p6xm, one underlying advisory; this is not zero-vulnerability approval. Documentation-only result updates followed verification and were format-checked separately.

## AF. LIMITATIONS AND REMAINING RISKS

1. Approved public-dataset access, source-specific rights and reviewed real-world annotations remain missing. Sender details are needed to submit the prepared request; publisher approval cannot be manufactured locally.
2. Full A–L independent timing, representative long-video memory/queue/drop/age measurements, and held-out calibration/test transfer remain incomplete.
3. CPU variability is large; CUDA/FP16 and mobile are unverified.
4. Only 36 diagnostic stills; correlated/source-selected data and tiny minority counts prevent deployment generalization.
5. Existing npm development-only advisory exception and optional-model/Java vulnerability review remain release-review items.

## AG. Task 006 verdict

**TASK 006 COMPLETE: NO**  
**SAFE TO START TASK 007: NO**

Task007 was not started.
