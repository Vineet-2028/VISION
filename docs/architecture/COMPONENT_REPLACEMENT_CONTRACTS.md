# Component replacement contracts

The critical loop is local. Web and Spring Boot do not own perception; Guardian
core owns authoritative geometry and timing. Optional detector libraries live only
inside laboratory adapters. Composition roots select adapters by configuration;
pipeline, recording, geometry and future tracking consume Sentinel values.

| Change                | Required change                                                                     | Contract that stays stable                                                  |
| --------------------- | ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Detector              | Adapter/runtime config, reviewed artifact hash                                      | DetectionBatch identity, original-image boxes, taxonomy and provenance      |
| Native to ONNX        | Runtime adapter and parity evidence                                                 | Same Sentinel output; no tensor types downstream                            |
| Input resolution      | Supported adapter setting, new configuration hash, recalibration of operating point | Exact inverse ImageTransform                                                |
| Camera/calibration    | Explicit calibration revision, dimensions, distortion and extrinsics                | Guardian camera math; no inferred physical calibration                      |
| Dataset version       | New immutable manifest and annotation provenance                                    | Versioned schema; historical results unchanged                              |
| Depth or segmentation | Future adapter and versioned output contract                                        | Source time, frame identity, explicit unavailable state                     |
| Tracker               | MultiObjectTracker implementation/configuration                                     | Immutable TrackSet, TrackId, original-image box and source observation time |

Task007 input is DetectionBatch: source ID, sequence index, observation nanoseconds,
timing provenance, semantic category, detector score (not calibrated probability),
continuous original-camera pixel box, model/runtime/configuration/transform hashes.
Raw model boxes may be off-image. Conversion to normalized Guardian Detection2D
requires an explicit clipping/rejection policy; the bridge rejects invalid boxes.
Unavailable calibration/rays remain unavailable, never NaN or a fabricated zero.

Physical-camera exposure timing and actual calibration are not established by
screen-recording PTS. Future tracking can use recording-time research observations,
but must not infer metric positions from placeholder intrinsics.

Depth and local motion evidence are implemented in Tasks008/009; the world model remains unimplemented. Candidate review samples may later refer
to source hash, source timestamp and reason (miss, uncertainty, track failure,
feedback). They must enter a new draft annotation version and independent review;
they cannot silently change an existing qualification set.

Schema migration is explicit: retain old readers/results, reject unknown versions,
write a new artifact with source hash and migration version, validate before use.
Never rewrite historical evidence in place. Runtime or camera changes invalidate
frozen operating points until their calibration protocol is repeated.

Dataset schema3 retains schema2 temporal guards and adds annotation-only SHELTER
context. Detector taxonomy `sentinel-coco-p0-v1` is unchanged. P0 evaluators exclude
context truth, but do not ignore false P0 predictions overlapping context objects.
Older dataset schemas reject this label rather than silently reinterpreting it.

Task007 implements optional image-space tracking in the desktop lab. Detector adapters
still return the same DetectionBatch. The pipeline sends raw recovery-floor proposals
to tracking and publishes detector results at a separate configured threshold. Tracker
code imports no model runtime. IoU, motion and two-stage policies return the same
immutable TrackSet; injected implementations satisfy MultiObjectTracker. The owner
explicitly resets sessions and closes the component on success, cancellation and failure.

Recording schema2 adds optional tracks; tracker-disabled records retain schema1.
TrackSet schema1 includes session/source/frame/time identity, observed-versus-predicted
status, box, category, bounded history and provenance. A future depth observation can
join these keys without exposing filter matrices. Ego-motion may later replace the
association predictor behind the protocol; it must retain explicit coordinate/time
contracts. Depth and motion extensions are implemented for prototype research; physical accuracy remains unvalidated.

## Task009 replacement boundary

Flow providers return immutable sparse/dense Sentinel pair observations. Dense providers adapt to bounded sparse correspondences for visual geometry. EgoMotionEstimator consumes those values and returns CameraMotionEstimate; visual, timestamp-aligned IMU and explicit research PnP share that contract. Detector and tracker observations are optional masks/sampling inputs. Neither is required to compute flow. Depth-free visual/rotation paths remain functional. No model or OpenCV object enters a world-model contract.

TrackImageMotionObservation retains session/pair/time, pixel displacement/rate and compensation kind. Residual is never a physical object velocity. Future semantic exclusion can implement SemanticExclusion. See docs/motion and the Task009 report for executed replacement evidence and limitations.
