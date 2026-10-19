# Task001–006 integration audit

Date: 2026-10-17. Read-only inspection preceded Task006C edits. Existing 36-image
diagnostic predictions reproduced at confidence .25 / IoU .5: YOLO26n 129/37/83,
YOLO26s 152/54/60, YOLO11n 132/47/80, RT-DETR 188/363/24 (TP/FP/FN).
Historical evidence is retained. No formal Task000 artifact exists; audit begins at Task001.

| Boundary                       | Status  | Evidence and limits                                                                                                                           |
| ------------------------------ | ------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| 001 → 002                      | PASS    | Root verify and backend/lab CI build guardian-core; Java8 target on JDK21; no Spring or UI runtime dependencies                               |
| 002 → 003                      | PASS    | Shared finite-value validation, Hamilton wxyz quaternions, explicit spatial frames and SI units; camera projection stays in core              |
| 003 → 004                      | PASS    | Capture-time pose/extrinsic chain checked; rolling-shutter rows use explicit timing; interpolation does not extrapolate                       |
| 004 → 005                      | PASS    | PTS identity stays separate from processing clock; observation-time scheduler, bounded queues and stale-result rejection                      |
| 003 → 005                      | PASS    | Exact integer resize/crop/pad transforms via JPype; resolution mismatch rejected; analytical inverse tests                                    |
| 005 → 006                      | PASS    | Sentinel DetectionBatch, frame/time/provenance retained; successful empty output differs from failure; adapters selected at composition roots |
| 006 → real-world qualification | PARTIAL | Reviewed, frozen six-candidate evaluation executed; single-recording/model-assisted bias prevents independent generalization claims           |

## Adversarial findings and fixes

**CRITICAL, addressed:** applying same-set diagnostic operating points to new data
as held-out qualification would leak threshold selection. Separate freeze and
qualification commands now enforce CALIBRATION/TEST roles, identical dataset/model/
configuration provenance and read-only frozen thresholds. Draft annotations fail validation.
The legacy public diagnostic CLI path rejects real-world datasets entirely; real-world
analysis requires reviewed annotations and the freeze/frozen workflow.

**HIGH, addressed:** whole-file split allocation cannot create independent splits
from one long recording. Schema-v2 windows retain parent hash and bounds; overlapping
windows and cross-split gaps below 60 seconds are rejected. TRAIN_DEV is excluded
from calibration/qualification analysis. These windows remain correlated; the policy
does not claim independent recordings or detect every re-encoded duplicate.

**HIGH, addressed during model validation:** YOLOX historical tag preprocessing
did not match the downloadable artifact. Initial diagnostic runs produced no .25
detections and are excluded from candidate evidence. Current official inference uses
raw BGR; the adapter now follows that path and a regression test asserts exact input
channel values. Do not compare invalid initial runs with corrected runs.

**HIGH, addressed:** PicoDet's graph embeds confidence .025 and NMS .6. The adapter
rejects confidence below the graph's floor and reports combined runtime/NMS timing.
No nonexistent low-threshold predictions are inferred.

**HIGH, original evidence gate superseded:** the user supplied reviewed annotations
and explicitly corrected the confirmed shelter label. All six candidates completed
calibration and froze their settings before TEST inference. The October 18 reviewed
qualification report records the results and decision. Model-assisted annotation
bias and single-recording correlation remain; this is not independent safety validation.

**HIGH, addressed:** realtime catch-up admission could continuously decode when
decoding was slower than the media clock, starving all component processing. A
600-second source replay exposed 18,001 drops and zero processed frames. Catch-up
now yields to processing after at most 32 admissions. A controlled-clock slow-decoder
regression verifies processing occurs before end of stream and accounting remains
complete. This prevents starvation; it does not make a slow decoder real-time.
The measurement wrapper now rejects zero-component-output runs even on exit code 0.

**HIGH, addressed:** evaluation image/video readers previously let FFmpeg auto-select
any demuxer. A local manifest-like file could therefore reference other resources.
These boundaries now restrict demuxers to supported image/video types and protocols
to local files, consistent with the replay source boundary. Existing decode tests pass.

**MEDIUM:** CPU timings vary with power, background tasks and thermal state; GPU is
optional and unverified. Decoder and native inference calls are synchronous and not
preemptible. Stale results are dropped after return; this is not a hard real-time
deadline guarantee. Combined vendor timing and annotation imbalance remain disclosed.

**LOW:** upstream model extension points and pinned preprocessing need upgrade tests.

## Architecture, memory and privacy

No model libraries enter guardian-core, web or Spring Boot. Tensor formats stay in
adapters/export tooling. Python bbox matching/NMS is evaluation/vendor work, not a
second camera, quaternion, TTC or CPA implementation. JVM startup is guarded once
per process; no per-frame/per-detection startup. Four corners cross JNI per restored
box; no per-pixel JNI. Benchmark preparation reparses synthetic identity calibration
per still, excluded from inference timing; replay constructs its geometry once.

Pipeline queues and metric windows are bounded. Results retain values, not image
buffers. Decode buffers close in finally paths. Session JSONL streams to disk; debug
images require explicit opt-in and a finite cap. Recording is synchronous and its
cost is measured; it can reduce throughput. Adapters must remain single-owner because
some runtime thread settings are global. No executor or per-frame threads are added.

User media, sampled images, proposals, review files and model weights are gitignored.
Preparation fails if raw media is tracked/unignored and checks source hashes again
after decode. Public reports contain no private absolute source paths. No upload,
identity recognition or telemetry feature is added; Python offline enforcement is
not an OS/native-code sandbox. Confidence is a model score, not calibrated certainty.
Geometry quality retains UNKNOWN/INVALID/VALID states; failures are not zero detections.

## Schema and configuration audit

Calibration/LabConfig use strict version1 schemas. Dataset v1 is preserved; v2 adds
parent temporal windows and TRAIN_DEV; v3 adds annotation-only SHELTER context.
Context is excluded from P0 truth without ignoring false P0 predictions. Unknown versions fail. DetectionBatch rejects
unknown taxonomy versions; session envelopes and benchmark artifacts carry schema1.
They are output records, not an implicit permissive deserialization API. Frozen
threshold artifacts reject unsupported version/source and bind original hashes.

LabConfig binds source, calibration, preprocess, runtime/hash, threshold, scheduler,
queue policy and recording. Public configuration omits paths but is hashed; source
and calibration provenance are stored separately. Geometry-critical calibration is
never silently inferred. Inventory configuration is hash-bound. Synthetic identity
intrinsics used for bbox diagnostics are explicitly not physical calibration.

## Executed evidence

`npm run check:lab`: PASS, 167 tests after the shelter-context and large-manifest
regressions; Ruff and strict mypy passed in that continuation.
Spatial and temporal contract tests passed. Full repository verification and real
model/replay results are recorded in the Task006C final report, separately from this
static boundary audit. No Task007 implementation was started.
