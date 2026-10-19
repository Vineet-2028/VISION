# Task009 adversarial audit

Scope: local prototype/research, Task001-008 boundaries plus all Task009 implementation. This is not production-safety certification. Task010 is not implemented.

## Pre-task read-only audit

Inspected the Task008 report/audit and Task001-008 integration audit, frame/detection/track/depth contracts, Guardian intrinsics/model/image transforms, PoseHistory/IMU/rolling shutter, sources/scheduler/recording, dependency locks and performance/replacement documents before edits. Observation and processing timestamps remain separate; relative depth rejects meters; detector, tracker and depth boundaries remain replaceable. Existing image-space tracker rates are not physical velocity. New explicit session binding was necessary for flow pairs.

Initial verification hit restricted pytest temporary-directory permissions. The elevated baseline showed 189 core and 228 lab tests passing; its later process result was unavailable after the continuation. It is not recorded as a full baseline pass. A subsequent full verification attempt during replay correctly failed Maven clean because Windows held the running JVM JAR. Final verification is run after replay releases it.

## Findings and fixes

| Severity                    | Files                              | Problem / consequence                                                                           | Resolution                                                                                                                     |
| --------------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| CRITICAL guarded            | flow.py, flow_runtime.py           | Reversed time, wrong session or resized-vector mistakes would corrupt motion                    | Ordered pair/session/source/calibration contracts; both endpoints restored; analytical rejection/resize tests                  |
| CRITICAL fixed during audit | flow_runtime.py                    | Direct provider caller could supply a mapping with incorrect dimensions                         | Mapping/image/camera dimensions and identity now checked before native flow; regression test                                   |
| CRITICAL guarded            | motion_geometry.py, ego_runtime.py | Distorted raw pixels or relative/stale depth could fabricate pose/scale                         | Guardian rays; exact frame-A metric-only PnP; explicit UP_TO_SCALE and UNVALIDATED_SCALE; distorted-camera regression          |
| HIGH fixed                  | pipeline.py                        | Injected flow could belong to another session even when ego was disabled                        | Unconditional published-flow session check                                                                                     |
| HIGH fixed                  | recording.py                       | Generic serialization would copy dense fields; manifest might understate schema                 | Flow and motion excluded before generic serialization; compact schema4 and explicit matrix conversion                          |
| HIGH fixed                  | ego_runtime.py                     | Rotation inliers could cluster despite broad initial coverage                                   | Coverage checked on selected inliers as well as initial features                                                               |
| HIGH fixed                  | cli.py                             | Motion initialization failure could leave source/recorder/renderer open                         | Explicit cleanup around pipeline initialization                                                                                |
| HIGH guarded                | geometry.py, motion_imu.py         | Latest pose or reversed mount composition would create false rotation                           | Bounded exact/interpolated Task004 history; Java frame-checked composition and independent mount test                          |
| HIGH guarded                | motion.py, pipeline.py             | Predicted tracks could receive fresh residual; old arrays could accumulate                      | Observed exact-frame boxes only; no residual history; one previous gray frame; close and 2000-release tests                    |
| MEDIUM open                 | runtime/evaluation                 | CPU cadence and freshness fail under load; native inference is synchronous                      | Record failures and achieved cadence; keep offline prototype scope, profile before real-time qualification                     |
| MEDIUM open                 | ego_runtime.py                     | Coherent dynamic majority is not distinguishable from camera motion without additional evidence | Never claim high-confidence static-scene truth; optional masks and explicit degradation; add independent sensor/scene evidence |
| MEDIUM open                 | dataset/calibration                | Placeholder intrinsics, no metric/pose truth or synchronized real IMU; weak prototype tracking  | Obtain measured calibration and independent scenario/identity labels before physical or safety qualification                   |
| LOW open                    | motion_benchmark.py                | Some timing stages are aggregated and no dense debug visual export                              | Extend diagnostics when needed; do not claim every requested stage is independently timed                                      |

No neural checkpoint, telemetry, cloud upload, identity extraction, full SLAM, risk/attention logic or Task010 segmentation was introduced. OpenCV RNG/thread settings are process-global; the documented lab is single-owner. Concurrent independent estimators should be isolated in processes in future. RANSAC/features/dense resolution/history/queues are bounded.

See the Task009 report for final executed checks and measurements. No claim of zero defects or production safety.
