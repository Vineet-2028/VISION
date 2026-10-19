# Task 006 adversarial audit

Review scope: Task005 replay, scheduling, frame identity, geometry, recording and
failure handling; new detector contracts, adapters, metrics, acquisition/export
tools, benchmarks, optional dependencies, workflows and documentation. The
Spring Boot/web/core boundaries and their existing verification gates were also
inspected. Static inspection is separate from executed checks in the dated report.

## CRITICAL implementation findings resolved

- `detector_runtime.py`, `geometry.py`: the vendor's ideal resize-ratio inverse
  did not describe the actual rounded image dimensions. This can shift camera-space
  boxes used by later geometry. YOLO now retains tensor-space boxes privately and
  restores through the exact composed Task003 transform. Analytical resize, crop,
  letterbox and unequal rounded-axis tests cover the repair.
- `pipeline.py`: an incorrectly typed component result could be silently discarded.
  It now fails explicitly, alongside the existing source/frame/timestamp identity
  checks. Successful empty detections, NoOp output and inference failure remain
  distinct. A regression test verifies wrong output types are fatal.

## HIGH implementation findings resolved

- `detector_runtime.py`: vendor setup reset requested CPU thread counts. Comparing
  those runs as one-thread results would be invalid. The pinned predictor controls
  setup, resets the calling thread before inference, checks the effective setting,
  and explicitly configures ONNX Runtime. Early failed/uncontrolled runs are excluded
  from the published matrix. They remain local diagnostic artifacts.
- `rtdetr_runtime.py`: provenance originally omitted runtime size/confidence/device/
  precision/thread settings. The current fingerprint includes them and both processor
  configuration files. Original baseline reports separately contain these settings;
  repeat runs use the corrected provenance.
- `offline.py`: vendor settings alone were insufficient to enforce local operation.
  A tested Python audit hook now denies Python network activity before vendor import.
  This is not a native-code or OS sandbox. Hash-verified trusted checkpoints remain
  mandatory; arbitrary PyTorch pickle checkpoints must not be treated as data.

## Remaining qualification gaps

**HIGH — production validation, not a repaired implementation defect:** the COCO
subset has 36 deliberately class-selected stills and no verified walking, occlusion,
real low-light or camera-motion labels. Synthetic stress cannot replace those labels.
Consequence: no assistive-safety, long-video stability or representative robustness
claim is supported. Obtain an appropriately licensed, annotated Guardian evaluation
set and repeat the benchmark before production qualification.

**HIGH — deployment approval:** no candidate has completed distribution-specific
license review, actual target-device latency testing or product acceptance gates.
Ultralytics' AGPL/enterprise terms remain material. No model passes the production
selection policy merely because its research metrics are better. Resolve licensing
and define validated recall, false-positive, freshness and resource requirements.

**MEDIUM — timing resolution:** YOLO's NMS/confidence filtering remain one vendor
stage; output conversion/class mapping/inverse geometry remain combined. RT-DETR
processor internals are combined. Whole-process memory includes JVM/import/decode
overhead. These limits are disclosed rather than represented as finer measurements.

**MEDIUM — statistical evidence:** single laptop runs have uncontrolled power,
thermal and OS scheduling effects. Repeat measurements are retained; an apparent
resolution/runtime speed advantage is not a statistically established ranking.
Only 24 tiny objects and seven motorcycles are present. Expand the dataset and
repeat runs on a controlled target before setting acceptance thresholds.

**MEDIUM — dependency review:** optional model dependencies are pinned separately
and `pip check` verifies compatibility, not vulnerability freedom. Generic CI does
not install them. Existing Java dependency vulnerability review and the documented
npm development-only advisory exception remain release-review items. See
`docs/security.md`; no blanket security approval is implied.

**LOW — vendor maintenance:** the YOLO predictor override and RT-DETR static legacy
ONNX export use pinned runtime behavior. Upgrade only with repeated geometry,
class/count/score/box parity and real-model checks. Export tracer warnings limit
RT-DETR's validated shape to batch one at 640, not arbitrary dynamic inputs.

**Resolved setup defect:** `detector_runtime.py` set the vendor cache location but
did not create its parent before import. Ultralytics therefore generated settings
under the repository root and formatting failed. The adapter now creates the
controlled directory first; a regression test verifies ordering. The generated
root settings were removed. This initialization-only change does not change model
preprocessing, inference or metric results from the recorded experiments.

## Boundaries, privacy and concurrency

- Model code stays in the optional desktop lab. Guardian-core retains zero runtime
  dependencies; web/API do not import model code. No tracking/depth/risk implementation
  was introduced. Task007 was not started.
- Adapters are synchronous, single-owner workers. Global runtime thread settings and
  network denial mean unrelated workloads should use separate processes. No hard
  cancellation is claimed; scheduling overruns and stale-result rejection are explicit.
- Benchmark files retain detections and public dataset references. No images, videos,
  model weights or local vendor settings are committed. Error-review export is bounded.
  Recorded source timing for independent stills is explicitly synthetic, not camera time.
- A filename-only scan of source/configuration found no common private-key, GitHub-token,
  AWS-access-key or OpenAI-project-key patterns. This limited scan is not proof that no
  possible secret exists. No secret values are included in this report.
- Generic CI tests contracts/metrics/geometry without real weights. Manual model CI
  checks checkpoint hashes and fails on errors; it uploads only diagnostic JSON.

## Executed validation

The final dated report records exact test/build results, export/parity outcomes,
benchmark counts and unverified items. Final `npm run verify` passed on 2026-10-15: 334 tests, static checks,
web/API builds, security policy and production smoke checks. The cache-location
repair was also verified by loading a real model. No known CRITICAL/HIGH
implementation defect remains from this pass. Production qualification remains
open independently of test success.
