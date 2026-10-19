# Task006C reviewed qualification — 2026-10-18

This report supersedes the pre-review completion status of October 17. Task007 has not started.

## A–G. Dataset, split and annotation evidence

A/B. One user-owned local recording: H.264, 1906×876, 1,350,371,295 bytes, 44,965 decoded frames, 1,498.833333334 seconds, time base 1/30000. Media hash: `e011aa64a65aa9aeb00fce657312362742d12dfd9170f76878e2a784ab1fc5e2`.

C/D. TRAIN_DEV [0,551.533333333), CALIBRATION [611.533333333,956.241666666), TEST [1016.241666666,1498.833333334), seconds. Two 60-second guard bands; these are correlated windows of one recording, not independent recordings.

E. Deterministic 2 Hz PTS grid, at least 3-second review spacing, average-hash Hamming distance greater than 3: 182 TRAIN_DEV / 115 CALIBRATION / 161 TEST frames. Prior independent packet-PTS verification matched every sampled timestamp.

F. All 458 frames carry user-reviewed flags. The user-confirmed frame-37 shelter is preserved as annotation-only SHELTER; 12,324 P0 boxes and one context box. Original review exports remain unchanged. No other TRAIN labels were relabeled. Structural validation and image/annotation hashes passed; this does not independently prove semantic accuracy or completeness. Only four frames had box/class edits relative to the proposals before the shelter correction. Model-assisted annotation bias is substantial.

Manifest SHA256: `5aaffcd6ec428805e90404633b32d0f340f63ba1a34c8d0a075ba8f5a9275b21`.

G. Qualification truth counts: PERSON=2790, MOTORCYCLE=731, BICYCLE=123, CAR=843, BUS=152, TRUCK=287, TRAIN=8, DOG=1. All frame scenario attributes remain UNKNOWN. Counts describe this reviewed dataset only.

## H–J. Candidate, license and export evidence

Six viable candidates were evaluated. YOLO26n/26s/11n use native 640 inputs; RT-DETRv2-R18 uses native 640; official YOLOX-Nano and PicoDet-S exports use fixed 416. All use CPU FP32, batch one, one model thread, five warmups and score floor .03. Different resolutions are declared candidate configurations, not an equal-resolution architecture experiment.

RTMDet-Tiny was attempted; no compatible binary MMCV was available for the existing Windows/Python environment. No execution is claimed. Existing four native/ONNX pairs passed prior public-subset parity. New YOLOX/PicoDet native parity is NOT VERIFIED.

YOLO models remain research references. RT-DETR has an Apache-2.0 model card; YOLOX/PicoDet repositories are Apache-2.0 but commercial checkpoint rights remain WEIGHTS_LICENSE_REVIEW_REQUIRED. This is local research selection, not product approval. See [third-party BOM](../../legal/THIRD_PARTY_MODEL_AND_DATA_BOM.md).

## K–L. Frozen calibration and held-out qualification

All six calibration artifacts were frozen before any TEST inference. Main policy: 100 FP per 100 calibration frames, IoU .5. No TEST retuning. Other frozen FP, precision and recall policies, including unavailable targets, are retained in the [machine-readable summary](task006c-reviewed-2026-10-18.json). TEST FP burden may exceed the calibration budget.

| Candidate     | Frozen score | Calibration TP/2463 | Calibration FP/115 frames | TEST TP/4935 (recall) | TEST FP/161 frames | Precision TP/(TP+FP) | FP/100 frames |
| ------------- | ------------ | ------------------- | ------------------------- | --------------------- | ------------------ | -------------------- | ------------- |
| yolo26n       | 0.25         | 782                 | 111                       | 1463/4935 (29.65%)    | 184                | 1463/1647 (88.83%)   | 114.29        |
| yolo26s       | 0.42         | 724                 | 111                       | 1321/4935 (26.77%)    | 160                | 1321/1481 (89.20%)   | 99.38         |
| yolo11n       | 0.27         | 798                 | 108                       | 1488/4935 (30.15%)    | 203                | 1488/1691 (88.00%)   | 126.09        |
| rtdetr-v2-r18 | 0.64         | 652                 | 110                       | 1190/4935 (24.11%)    | 198                | 1190/1388 (85.73%)   | 122.98        |
| yolox-nano    | 0.15         | 1005                | 106                       | 1966/4935 (39.84%)    | 260                | 1966/2226 (88.32%)   | 161.49        |
| picodet-s     | 0.25         | 1887                | 0                         | 3706/4935 (75.10%)    | 1                  | 3706/3707 (99.97%)   | 0.62          |

These metrics measure agreement with user-reviewed model-assisted labels. In particular, the proposal generators can be favored by retained proposal boxes. Do not interpret near-perfect precision as independently established real-world precision.

## M. Class-specific qualification

Each cell is matched / truth count (recall); zero truth means NOT AVAILABLE. Rare classes and one-recording counts do not establish population performance.

TRAIN (8 objects) and DOG (1 object): **INSUFFICIENT_DATA** for class performance claims.

| Candidate     | PERSON             | BICYCLE          | MOTORCYCLE       | CAR              | BUS              | TRUCK            | TRAIN        | DOG           |
| ------------- | ------------------ | ---------------- | ---------------- | ---------------- | ---------------- | ---------------- | ------------ | ------------- |
| yolo26n       | 930/2790 (33.33%)  | 8/123 (6.50%)    | 181/731 (24.76%) | 258/843 (30.60%) | 19/152 (12.50%)  | 65/287 (22.65%)  | 2/8 (25.00%) | 0/1 (0.00%)   |
| yolo26s       | 850/2790 (30.47%)  | 5/123 (4.07%)    | 147/731 (20.11%) | 243/843 (28.83%) | 20/152 (13.16%)  | 55/287 (19.16%)  | 1/8 (12.50%) | 0/1 (0.00%)   |
| yolo11n       | 952/2790 (34.12%)  | 8/123 (6.50%)    | 174/731 (23.80%) | 264/843 (31.32%) | 28/152 (18.42%)  | 61/287 (21.25%)  | 1/8 (12.50%) | 0/1 (0.00%)   |
| rtdetr-v2-r18 | 869/2790 (31.15%)  | 5/123 (4.07%)    | 0/731 (0.00%)    | 244/843 (28.94%) | 22/152 (14.47%)  | 48/287 (16.72%)  | 2/8 (25.00%) | 0/1 (0.00%)   |
| yolox-nano    | 1118/2790 (40.07%) | 26/123 (21.14%)  | 287/731 (39.26%) | 383/843 (45.43%) | 50/152 (32.89%)  | 99/287 (34.49%)  | 3/8 (37.50%) | 0/1 (0.00%)   |
| picodet-s     | 2114/2790 (75.77%) | 104/123 (84.55%) | 520/731 (71.14%) | 586/843 (69.51%) | 129/152 (84.87%) | 245/287 (85.37%) | 7/8 (87.50%) | 1/1 (100.00%) |

## N. Image-space size results

Area/image-area buckets: TINY <.001, SMALL [.001,.01), MEDIUM [.01,.1), LARGE ≥.1. These are image-space proxies, not distance estimates.

TINY has only eight objects: **INSUFFICIENT_DATA** for a tiny-object robustness claim.

| Candidate     | TINY          | SMALL              | MEDIUM             | LARGE            |
| ------------- | ------------- | ------------------ | ------------------ | ---------------- |
| yolo26n       | 1/8 (12.50%)  | 487/2322 (20.97%)  | 873/2408 (36.25%)  | 102/197 (51.78%) |
| yolo26s       | 2/8 (25.00%)  | 449/2322 (19.34%)  | 777/2408 (32.27%)  | 93/197 (47.21%)  |
| yolo11n       | 0/8 (0.00%)   | 508/2322 (21.88%)  | 882/2408 (36.63%)  | 98/197 (49.75%)  |
| rtdetr-v2-r18 | 2/8 (25.00%)  | 434/2322 (18.69%)  | 673/2408 (27.95%)  | 81/197 (41.12%)  |
| yolox-nano    | 0/8 (0.00%)   | 734/2322 (31.61%)  | 1118/2408 (46.43%) | 114/197 (57.87%) |
| picodet-s     | 8/8 (100.00%) | 1770/2322 (76.23%) | 1757/2408 (72.97%) | 171/197 (86.80%) |

## O–Q. Motion, light and crowd/occlusion

NOT AVAILABLE: no reviewed subgroup labels. Overall real-video results cannot substitute for these slices. Synthetic historical stress tests remain separate.

## R. Matched localization

Only IoU ≥.5 matches contribute; misses remain in recall denominators above. Center and bottom-center Euclidean errors normalize x by width and y by height.

| Candidate     | Matches | Mean IoU | Mean center error | Mean bottom-center error |
| ------------- | ------- | -------- | ----------------- | ------------------------ |
| yolo26n       | 1463    | 0.82586  | 0.00948           | 0.01032                  |
| yolo26s       | 1321    | 0.81879  | 0.00968           | 0.01065                  |
| yolo11n       | 1488    | 0.82356  | 0.00947           | 0.01059                  |
| rtdetr-v2-r18 | 1190    | 0.82751  | 0.00837           | 0.01022                  |
| yolox-nano    | 1966    | 0.97146  | 0.00168           | 0.00212                  |
| picodet-s     | 3706    | 0.98576  | 0.00093           | 0.00094                  |

Per-group bottom-center errors and matched denominators are included in the JSON summary.

## S–T. Sustained replay and result age

Prior PicoDet replays use confidence .25, which matches its frozen operating point. New YOLOX runs use its frozen .15 score. The ten-minute YOLOX run overlaps qualification workloads; the subsequent short cadence runs do not. These remain desktop observations, not isolated speed measurements. Different dates, durations and background load prevent a controlled cross-model speed ranking.

| Run                 | Wall seconds | Detector outputs | Achieved detector Hz (source duration) | Decoded / processed / dropped / failed | Peak queue | Age P50/P95/P99 ms       | Peak sampled tree RSS MiB |
| ------------------- | ------------ | ---------------- | -------------------------------------- | -------------------------------------- | ---------- | ------------------------ | ------------------------- |
| picodet-5hz-bounded | 603.48       | 1459             | 2.43                                   | 18001 / 3415 / 14586 / 0               | 1          | 212.29 / 290.74 / 355.52 | 207.66                    |
| picodet-10hz        | 63.17        | 361              | 6.02                                   | 1801 / 616 / 1185 / 0                  | 1          | 75.06 / 262.32 / 306.48  | 208.66                    |
| yolox-frozen-5hz    | 602.05       | 2696             | 4.49                                   | 18001 / 12922 / 5079 / 0               | 1          | 41.92 / 130.08 / 146.30  | 196.69                    |
| yolox-frozen-10hz   | 62.14        | 600              | 10.00                                  | 1801 / 1761 / 40 / 0                   | 1          | 46.15 / 58.16 / 65.23    | 194.55                    |

Detector output cadence is not frame-processing cadence. Full stage timing, RSS start/end/sample counts, drop accounting and hashes are retained in the JSON. Metrics are bounded samples, not a leak proof or hard deadline guarantee. The research stale limit is two seconds; native decode/inference is non-preemptible. No mobile performance is inferred. Earlier zero-output PicoDet replay remains failed evidence and is excluded; bounded catch-up admission and zero-output rejection corrected that defect.

After the 10 Hz check achieved 600/600 scheduled results, a 60-second 15 Hz request
delivered only 660 results (11 Hz), with 608 dropped frames, zero failures, queue
depth one, P95/P99 age 125.77/131.60 ms and peak sampled RSS 204,423,168 bytes.
The 15 Hz target was **not met**; do not configure it as a guaranteed cadence.

The 600-second YOLOX run delivered 2,696 results; its percentiles cover the latest
2,048 results, not all 2,696. Short-run and PicoDet detector-age windows contain
all their detector results. Memory start/end includes process startup/teardown and
does not isolate model allocations.

## U–Z. Training and provisional detector decision

**PRIMARY_TASK007_DETECTOR: PicoDet-S416 ONNX, CPU FP32, one thread, confidence .25.**

**FALLBACK_TASK007_DETECTOR: YOLOX-Nano416 ONNX, CPU FP32, one thread, confidence .15.**

The primary favors observed P0/class/size recall at the frozen policy and compact export; the fallback offers a different implementation and a measured CPU cadence alternative. Both remain replaceable research adapters. PicoDet proposal bias prevents calling its observed advantage an independent generalization win. Its cadence shortfall also prevents treating 5–10 Hz requests as guaranteed delivery. Future tracking must consume actual observation timestamps, handle gaps and never infer continuous detection availability.

U/V. **Training NOT TRIGGERED; fine-tuning NOT RUN.** These pretrained outputs are sufficient to begin bounded local tracking research and contract development, not hazard detection deployment. Fine-tuning now risks learning retained proposal errors from a single correlated recording. Improved independent annotation and new untouched evaluation data are required before optimization driven by these TEST results. Do not train on TEST.

Z. **PRETRAINED_SUFFICIENT_FOR_TASK007_RESEARCH: YES**, limited to offline/local tracking engineering, explicit missing detections and no user-facing safety claims. No production accuracy, licensing or latency acceptance gate has been passed.

## AA–AJ. Integration, architecture and privacy

AA. Boundaries 001→002, 002→003, 003→004, 004→005, 003→005 and 005→006: **PASS for tested software contracts**. Real-world evaluation: executed with the annotation/single-recording limitations above; independent generalization remains PARTIAL. See [integration audit](../../architecture/TASK001_006_INTEGRATION_AUDIT.md).

AB. Analytical spatial tests cover inverse letterbox, original-image Detection2D, camera ray and bearing. AC. Temporal tests cover capture-time interpolation and CAMERA→DEVICE→WORLD transforms. AD. Synthetic A/B swaps and real YOLOX/PicoDet replays exercise the same downstream contracts. These are not sensor calibration validation.

AE/AF. Model libraries remain inside adapters. Guardian Java owns camera/time math; JPype starts once per process. Queues, catch-up admission, metrics and debug persistence are bounded. Results do not retain raw frames. No new tracking, risk or attention system was implemented. Native calls remain synchronous; finite queue size is not a real-time deadline.

AG. No user footage upload or recognition/telemetry feature was introduced. Media, review exports and weights remain local and ignored. Summary reports omit private paths and images. Python offline guards are not an OS sandbox. Physical intrinsics remain UNKNOWN.

AH. The BOM separates framework, checkpoint and dataset rights. AI. New data/annotation versions preserve historical hashes and results; schemas 1/2 remain readable, schema3 adds context SHELTER, unknown versions fail. AJ. Task007 consumes vendor-free DetectionBatch with original-image coordinates, observation identity/time, score and provenance. It must not derive metric positions from placeholder camera intrinsics. See [replacement contracts](../../architecture/COMPONENT_REPLACEMENT_CONTRACTS.md).

## AK–AN. Verification and verdict

**Executed `npm run verify`: PASS, exit code 0, 2026-10-18.**
Private log: `benchmark-results/task006c/verify-qualified-2026-10-18.log`.

AK. **383 tests passed:** Guardian core 189, perception lab 167, web 24, API 3.
AL. Formatting, Ruff, strict mypy (27 modules), ESLint, strict TypeScript,
Spotless, SpotBugs, Java builds and the production Next.js build passed.
Production smoke passed API contracts, home page, eight concurrent health requests
and API outage handling. `pip check`, review-editor JavaScript syntax and
`git diff --check` also passed. Hosted GitHub Actions were not executed here.

Security policy passed with five reviewed development dependency entries for
GHSA-vfj7-8cjw-p6xm; this is not zero vulnerabilities. Docker was not run, consistent
with local-only development. Android checks are N/A because Android was removed
by project direction. Architecture contract checks passed within the limits above.

### Adversarial audit findings

- **CRITICAL: no new open implementation finding.** Earlier split/threshold leakage
  risks are guarded by reviewed annotations, parent windows, frozen settings and
  provenance checks. These do not remove correlation or annotation bias.
- **HIGH: no new open implementation finding.** Earlier scheduler starvation,
  model preprocessing, local decoder restrictions, shelter scoring and the runtime
  configuration size limit incorrectly applied to datasets were corrected and
  covered by regression checks. See the integration audit for affected modules.
- **MEDIUM — annotation evidence:** `datasets/sentinel_first_person_v1/` and this
  report. Model-proposal bias, one parent recording and unknown scenario labels
  limit generalization. Use independent reviewed annotations, additional recordings
  and new untouched evaluation versions before optimizing or making robustness claims.
- **MEDIUM — runtime cadence:** `apps/perception-lab/src/perception_lab/pipeline.py`
  and replay artifacts. Native calls are synchronous; 5/15 Hz requests can be missed.
  Consumers must use observation timestamps and handle unavailable/stale results;
  measure deployment hardware before setting operational budgets.
- **MEDIUM — export and rights evidence:** `configs/detector-checkpoints.json` and
  the third-party BOM. Native parity for the new ONNX candidates and commercial
  checkpoint rights remain unverified. Obtain that evidence before redistribution
  or production selection; do not label these models production approved.
- **LOW — local editor UI:** `tools/annotation-review.html`. Syntax and import
  tests pass, but automated browser interaction was blocked by browser file-URL
  policy. User review exports were received; a separate editor interaction test
  remains useful before a larger annotation campaign.

Known unverified items also include mobile/GPU performance, physical camera
calibration/exposure timing, independent scene robustness, RTMDet execution,
hosted CI execution and deployment security. Android is intentionally absent;
Docker is outside the requested local workflow. No production-safety claim follows
from these tests. The documented development dependency advisory remains governed
by the repository security policy; a green policy check is not zero vulnerabilities.

AN. **TASK006 COMPLETE: YES. TASK006C COMPLETE: YES.**
**ENGINEERING QUALIFIED FOR TASK007: YES.**
**PRETRAINED_SUFFICIENT_FOR_TASK007_RESEARCH: YES.**
**PRODUCTION_SAFETY_VALIDATED: NO.**

This closes the local research engineering gate, not the deployment/safety gate.
Task007 may start as bounded local tracking research using the documented inputs
and missing-detection handling. No Task007 implementation was started in this pass.
