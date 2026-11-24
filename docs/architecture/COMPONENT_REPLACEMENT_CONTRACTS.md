# Component replacement contracts

## Task010 semantic surfaces

`SemanticSegmenter.segment(PreparedImage, FrameIdentity)` returns `SemanticFrame` or explicit no output. Synthetic, PIDNet and PP-LiteSeg profiles share one taxonomy/mapping contract. `SurfaceEvidenceExtractor` consumes no model internals. Generic exact-frame detections/tracks can add separate occupancy; depth consistency is optional, and flow is not required. Native class IDs stay inside the adapter. Unsupported classes and checkpoint provenance remain visible.

Realtime results can be published after their source frame: use the nested semantic identity and age, never the enclosing publication identity for fusion. Stale results cannot provide current ground evidence. Task011/012 can replace providers without rewriting geometry/surface consumers. Propagation is deferred and must not silently change OBSERVED semantics.

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

Depth and local motion evidence are implemented in Tasks008/009; the world model is implemented in Task011. Candidate review samples may later refer
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

## Task011 replacement boundary

World model consumes Sentinel DetectionBatch/TrackSet, TrackDepthObservation, CameraMotionEstimate, TrackImageMotionObservation, SemanticFrame and SurfaceEvidenceFrame. It imports no vendor runtime or tracker implementation. Provider swaps change adapter/configuration only; fixture provenance swaps and actual detector replays verify the boundary. A separate WorldEntityId avoids hard-coding permanent tracker identity equivalence. WorldModel.consume/snapshot/reset/close is replaceable; Task012+ consume immutable WorldState schema 1. Recording schema 6 adds compact world state. Draft semantics remain UNVERIFIED; no replacement implicitly improves evidence quality.

## Task012 replacement boundary

CorridorAnalyzer consumes only immutable WorldState and publishes CorridorAnalysis. Detector/tracker/depth/flow/ego/segmenter changes remain upstream of that contract. Additive image geometry, supplied-plane and bounded surface-sample fields expose the information needed without leaking implementations. Synthetic provider A/B joins, an alternate WorldState producer/analyzer, actual PicoDet full replay and YOLOX partial replay exercise replacement. Missing new optional fields produce explicit unavailable/fallback states; unknown schema versions are rejected.

Guardian owns metric corridor geometry; Python selects valid evidence and provides an image heuristic. Body-heading or future personalized implementations may replace the analyzer without changing downstream entity IDs, timestamps, relation enums or explicit uncertainty. Recording schema7 preserves compact analysis. No new frameworks or model dependencies are required.

## Task013 replacement boundary

TrajectoryPredictor consumes WorldState and optional CorridorAnalysis, returning TrajectorySet schema1. CP, last-two CV, robust-window CV and adaptive policies share the immutable PredictedTrajectory contract; downstream receives no filter matrices or predictor class. World histories add optional bearing/world-point/source fields. Missing fields preserve image fallback; relative depth cannot satisfy world gates. Provider names never determine eligibility.

Alternate world provenance and large-count fixtures exercise the producer boundary. Raw image corridor comparison uses only the convex image polygon contract. Task013 leaves bearing/world/residual corridor mappings unavailable; Task014 adds matching world-plane interaction geometry. Recording schema8 preserves physical status, units, source observations, hypotheses, horizons and uncertainty. Interaction and future risk consumers must inspect evidence validity, not infer physical truth from the selected representation. No predictor output is written back as an observation.

## Task014 replacement boundary

InteractionAnalyzer consumes matching WorldState, CorridorAnalysis, TrajectorySet and optional ReferenceMotion. It emits InteractionAnalysis schema1; recording schema9 adds it without changing upstream adapters. CP, CV and alternate piecewise paths share one consumer. Actual detector replay plus synthetic producer/protocol fixtures exercise the boundary; provenance labels alone are not claims of testing every vendor model combination.

No detector/tracker/depth/flow/segmenter implementation enters interaction contracts. Current source quality and validity remain authoritative. Guardian Motion owns TTC/CPA, including the additive signed CPA query; Python owns eligibility and status policy. Future synchronized user velocity or metric sensors extend source authorization through ReferenceMotion/world contracts, without changing forecast consumers. No validated physical output can be enabled merely by changing a string. Future moving-corridor logic must supply explicit reference metadata rather than silently reusing frozen geometry. Task015 must consume these forecasts and must not recompute contact geometry.

## Task015 replacement boundary

RiskEngine consumes immutable WorldState, CorridorAnalysis, TrajectorySet and
InteractionAnalysis. No vendor inference or geometry implementation is imported.
RiskAssessmentSet schema 1 supplies Task016 with level, trend, quality,
reason codes, validity deadline, identity and provenance. Recording uses schema 10.
Injected-engine pipeline tests exercise the boundary; future weighted/physical
policies must satisfy the same unknown, freshness, identity and expiry regressions.
Future validated sensors strengthen source authorization, not change downstream equations.
Task016 attention implementation is documented below.

## Task016 replacement boundary

AttentionEngine.decide consumes only RiskAssessmentSet and optional AudioChannelState
with authoritative now_ns. It returns frozen AttentionDecisionSet schema1. Naive,
cooldown and novelty/escalation implementations share it; vendor inference and
geometry stay upstream. A different risk producer passes the same contract. The
weighted risk engine was deliberately not implemented in Task015, so no weighted
accuracy result is claimed. Unknown category/direction remain null, not guessed.
Pipeline injection, schema11 recording and reset are regression-tested. Task017
must discard expired intents and interpret silence without an all-clear claim.

## Task017 replacement boundary

AlertRenderer consumes frozen AlertIntent; AlertPresenter accepts frozen intent/presentation plus authoritative media-mapped time. Optional semantic evidence, source timestamp/basis and physical-validity fields extend AttentionDecision without changing prior constructor requirements. Missing fields remain unknown, not inferred from model labels. Current policies do not authorize direction/category wording.

Recording/null presenter and alternate renderer tests preserve the same contract. Naive, cooldown and novelty attention policies feed it unchanged. No geometry, risk or ML implementation is imported by the alert renderer. Schema12 records AlertOutputSet schema1 alongside prior end-to-end evidence for Task018. Reset cancels pending output; sinks must recheck expiry at actual consumption and never block the pipeline. See docs/alerts/ALERT_EVALUATION.md for exact joins and missing-data semantics.

## Task018 evaluation boundary

V0EventLedger schema1 is an evaluation-only frozen contract. StageOutcome stores status, source observation, optional measured age and reason. Reference status and provenance remain separate from runtime quality. Unknown evidence cannot establish a later first failure; the canonical prefix cannot resume after an earlier failed stage. Duplicate event identities are rejected.

The replay instrument subclasses Pipeline and SessionRecorder in local tools only; production consumers do not depend on it. Model adapters and policy implementations are unchanged. Replacing a provider requires the same normalized identities, units, timing and validity fields, plus a fresh frozen evaluation configuration. The canonical benchmark constructor currently supports PicoDet/YOLOX only; no other real-model replacement performance is claimed. Replacing a reference dataset requires source hash alignment and explicit reference-quality status, not just renaming a file.
