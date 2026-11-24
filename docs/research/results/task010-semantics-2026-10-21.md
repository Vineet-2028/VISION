# Task010 semantic surfaces report

Date: 2026-10-21. Local prototype/research only. This report distinguishes implementation, measurements and outstanding qualification.

## A. Pre-task audit

Read-only inspection of Task001–009 contracts, geometry, scheduler, recording, manifests, BOM and performance documents preceded integration. Baseline `npm run verify` exited 0 with 480 tests.

## B. Files changed

Added semantics, semantic configuration/runtime/worker/evaluation and surfaces modules; semantic tests; model export, benchmark/review/evaluation/replay tools; schema, example config and documentation. Updated optional component contracts, CLI/pipeline, metrics and recording. Prior Task009 changes remain preserved.

## C. Segmentation architecture

Model-independent SemanticSegmenter → immutable SemanticFrame → SurfaceEvidenceExtractor. Image-space evidence works without detector/tracker/depth/flow or physical intrinsics. No safety/world model.

## D. Semantic taxonomy

`sentinel-surfaces-v1`: 20 explicit classes; UNKNOWN=0, annotation-only IGNORE=255. Versioned Cityscapes train-ID mapping. Terrain stays broad GROUND_OTHER. Unsupported classes are recorded.

## E. SemanticFrame contract

Session, frame/source observation identity, native uint8 labels, Guardian affine mapping, taxonomy/mapping version, supported classes, provenance, processing timing, status, quality and age. Bytes-backed immutable mask ownership.

## F. Models evaluated

Actual PIDNet-S at 512×256 and 768×384, plus PP-LiteSeg at 512×512, each executed on the same 96 first-person images. Synthetic provider exercises analytical contracts. No SegFormer or training.

## G. License / checkpoint status

Research references only. MIT PIDNet code and Apache-2.0 PaddleSeg code do not settle checkpoint rights. Cityscapes lineage and separate weight permission require review. Exact source/checkpoint/export hashes and links are in the BOM. PIDNet synthetic native/export class agreement was 1.0 at both resolutions; PP-LiteSeg native/export parity remains unverified.

## H. Segmentation dataset

96 existing hashed frames: 32 TRAIN_DEV, 32 CALIBRATION, 32 TEST. Existing sequence/time/split identity preserved, evenly spaced selection. One parent recording does not establish cross-user generalization.

## I. Annotation review status

All 96 remain DRAFT_MODEL_ASSISTED. Every review pixel starts ignored. The local editor supports region acceptance/relabeling, painting, polygons, unknown/ignore, undo, export and resume. Human review is required; prior detection/track review is not segmentation approval.

## J. Model accuracy

UNVALIDATED pending human masks. No model proposal is treated as truth.

## K. Per-class results

Evaluator supports per-class IoU, precision, recall, Dice and support. Real values unavailable pending review.

## L. Sidewalk / road / path results

SIDEWALK/ROAD supported by both candidates. PATH/FLOOR are unsupported by these Cityscapes checkpoints and cannot be declared absent. Research sufficiency requires coverage review.

## M. False traversable evidence

Metric implemented and analytically tested, including obstacle-as-traversable pixel count and reviewed-proposal denominator. Real first-person value unavailable pending human review.

## N. Boundary quality

Ignore-aware one-pixel boundary precision/recall/F1 implemented and analytically tested. Missing predicted boundaries score zero when truth has a boundary. Real boundary accuracy awaits review.

## O. Surface evidence architecture

Separate compact evidence flags, exact-camera boundary mask and bounded region metadata. Road remains contextual; stairs/curbs never automatically become generic potential ground. No safe-path state.

## P. Bottom-connected ground results

Analytical disconnected-island test preserves both components and correctly distinguishes bottom contact. Real usefulness unvalidated.

## Q. Detection overlay results

Generic exact-frame object occupancy is separate from unchanged semantics. Oversized box overlay is diagnosed/ignored. Analytical detector provenance swaps pass; actual coexistence runs passed.

## R. Depth consistency results

Two synthetic depth provenances feed the same exact-frame/grid qualitative diagnostic. Known discontinuity produces nonzero relative-jump evidence. No curb height, metric slope or safety output.

## S. Temporal segmentation results

OBSERVED/PROPAGATED/STALE/UNAVAILABLE contracts implemented. Default no propagation. REALTIME worker retains one job, skips busy ticks and publishes original observation identity; expired results yield unknown-only surface evidence.

## T. Flow propagation results

DELIBERATELY DEFERRED. No flow warp, inpainting or propagated accuracy claim. Future implementation must preserve original time, exact pairs, unknown disocclusion and expiration.

## U. Low-light results

INSUFFICIENT REVIEWED SCENARIO DATA. Brightness alone is not a low-light label.

## V. High-motion results

INSUFFICIENT REVIEWED SCENARIO DATA. No unaligned pixel agreement is called temporal accuracy.

## W. Crowd results

INSUFFICIENT REVIEWED SCENARIO DATA. Person/vehicle semantics do not hallucinate observed ground behind occluders.

## X. Shadow / surface-texture results

UNVALIDATED. Scenario/texture annotation needed before stratified performance claims.

## Y. Cadence results

Independent semantic interval and one-job REALTIME load shedding implemented. 1 Hz sampled offline long replay is diagnostic, not a demonstrated real-time rate. No 2/5 Hz realtime qualification claim.

## Z. Result age P50/P95/P99

Source PTS remains separate from processing clock. Metrics distinguish semantic observation age and anchored realtime result age. Offline processing-age percentiles are reported with long replay; not sensor-to-publication freshness.

## AA. Latency P50/P90/P95/P99

96-frame comparison total P50/P90/P95/P99 ms: PIDNet512 1406.76/1825.88/2102.49/2336.81; PP-LiteSeg512 1883.93/2480.09/2696.69/2864.13; PIDNet768 2026.93/2522.96/2716.05/2962.46. Diagnostic total includes separate restoration plus extractor restoration. Concurrent local verification/replay affected timings; not isolated hardware qualification. Per-stage distributions are in the JSON.

## AB. Memory / long-run stability

Completed 600-second source replay: 18,000 decoded frames, 600 updates at requested 1 Hz PTS sampling, zero failures, zero queued frames. Wall time 1,014.55 s: this is not real-time throughput. Processing-age P50/P95/P99: 1100.28/1562.89/1920.66 ms. Sampled RSS start/peak/end: 168,513,536/237,834,240/223,555,584 bytes. Samples plateau after warm-up; this finite run is not proof against every leak. Replay predates the final provenance configuration-hash addition, so its recorded configuration hash remains null. Finite 96-frame packet preparation held all three proposal RLE sets and reached sampled RSS 666,480,640 bytes; this is offline packet construction, not runtime history. A 2,000-frame weak-reference test confirms old semantic arrays release.

## AC. Detector swap test

PicoDet-S and YOLOX-Nano each processed 90 frames with tracking, flow, synthetic depth and 3 semantic updates, zero failures. One end-boundary frame was deliberately skipped per run. Segmenter source was unchanged.

## AD. Tracker swap test

Generic alternate TrackSet fixture accepted; wrong-session tracks rejected. No tracker implementation dependency in surfaces.

## AE. Depth swap test

Alternate synthetic depth provenance tested through the same qualitative API. Real depth accuracy remains inherited/unvalidated; no claim of new real-depth qualification.

## AF. Flow / no-flow test

Segmentation-only replay and combined flow replay work. Fresh semantic inference takes no flow input. Propagation is deferred.

## AG. Segmenter swap test

Synthetic, PIDNet and PP-LiteSeg feed the same SemanticFrame/SurfaceEvidence contracts. Real two-provider comparison executed; no downstream provider branch.

## AH. Task001–010 integration audit

See TASK001_010_INTEGRATION_AUDIT.md for every boundary. Software interfaces pass; propagation, human accuracy, product rights and real-time safety remain partial.

## AI. Component replacement audit

Replacement contracts updated. Detector/tracker/depth/flow/ego/segmenter implementations remain behind their public contracts.

## AJ. Future Task011 contract

Documented optional identity-bound detections, tracks, depth, motion, semantics and surfaces. Task011 not implemented.

## AK. Future Task012 contract

Documented SurfaceEvidenceFrame plus camera/depth/pose consumers; corridor/free-space not implemented.

## AL. Pretrained sufficiency

NO — sufficiency is not yet demonstrated. This is a pending-evidence decision, not proof that pretrained models fail. Human surface labels and taxonomy coverage determine the next decision.

## AM. Primary segmenter for Task011

PROVISIONAL research comparison choice: PIDNet-S512, based on lower observed cost only. Available as a provisional local research adapter for exploratory Task011 integration only. Quality-based selection still requires reviewed error/coverage analysis; product use requires rights review.

## AN. Fallback segmenter

PP-LiteSeg512 is an explicit research alternate, not automatic failover or product-cleared fallback. Missing inference returns unavailable.

## AO. R&D experiments

20 structured RND-SEG questions recorded with hypothesis, experiment, metrics, decision criterion and status. No fabricated results.

## AP. Security / privacy

Local footage only, no upload, identity analysis or cloud telemetry. Checkpoints/images remain ignored. Public evidence omits private paths and raw images. UI browser attachment failed twice; no browser-visual pass claimed. JavaScript syntax passed for the template and generated page. HTTP serving was not verified (loopback request timed out); the handoff uses the self-contained local HTML with sibling images. The evaluator rejected the draft packet and created no score output.

## AQ. Adversarial audit

Read-only postimplementation inspection identified transform composition, stale-result handling, dense serialization risk and missing-boundary metric issues; fixes and regression evidence are in TASK010_AUDIT.md. Remaining MEDIUM items: human labels, rights, real-time contention/shutdown; LOW: richer bounded polygons/visualization.

## AR. Test counts

Final verification passed 511 tests: 189 Guardian core, 295 perception lab (including 31 semantic tests), 24 web, and 3 API. Ruff and strict mypy on 55 modules passed. Review-tool JavaScript syntax, RLE roundtrip and five malformed-mask cases also passed as separate checks.

## AS. Full verification

Final `npm run verify` exited 0 on 2026-10-21: formatting, core compilation/tests/SpotBugs, lab Ruff/mypy/pytest, web ESLint/TypeScript/tests/production build, API compilation/tests/SpotBugs, dependency policy and application smoke passed. Smoke covered API contracts, production home, eight concurrent health requests and API outage handling. Five previously reviewed development advisory entries remain; this is not a zero-vulnerability result. Log: `benchmark-results/task010-final-verify.log`. Documentation-only closeout edits were formatting-checked afterward. No hosted CI, cloud/mobile/Docker execution.

## AT. Remaining risks

No reviewed semantic accuracy, false-traversable or boundary-quality qualification; unsupported stairs/curb/path/floor; shared-parent data; unresolved checkpoint rights; real-time performance and production safety unvalidated.

## AU. Final verdict

TASK010 COMPLETE: YES — accepted local prototype engineering scope only. ENGINEERING QUALIFIED FOR TASK011: YES — exploratory integration with explicitly unverified semantic observations. HUMAN_VALIDATION: DEFERRED, NOT PERFORMED. PRETRAINED_SEGMENTATION_SUFFICIENT_FOR_TASK011_RESEARCH: NOT DEMONSTRATED. SAFE_PATH_VALIDATED: NO. PRODUCTION_SAFETY_VALIDATED: NO. Task011 has not started.

Acceptance scope was revised at the user's request on 2026-10-21 to allow prototype development to continue. This closes the engineering milestone, not the original reviewed-ground-truth qualification gate. All 96 frames remain DRAFT_MODEL_ASSISTED; no human review or accuracy result is fabricated. The evaluator still rejects unreviewed masks. Human review remains required before reporting ground-truth accuracy or qualifying a model. Checkpoint rights and real-time performance remain unresolved; milestone acceptance grants neither product clearance nor safety approval.
