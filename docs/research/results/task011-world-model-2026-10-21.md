# Task011 world model report

Date: 2026-10-21. Local prototype engineering, not safety qualification.

## A. Pre-task audit

Read-only review covered all requested contracts, Task001-010 audits, dataset schema, BOM, scheduler, recording, tests and Guardian geometry/PoseHistory. Baseline npm run verify exited 0: 511 tests. Existing limits retained: unverified semantics, unvalidated metric depth/physical motion and real-time limits.

## B. Files changed

Added world_config.py, world_types.py, world_model.py, test_world_model.py, tools/world_benchmark.py, example config and world-model/research/integration documentation. Extended optional config, FrameResult, Pipeline, metrics and recorder schema6. Preserved earlier uncommitted Task009/010 work.

## C. World model architecture

Single-writer bounded derived state over Sentinel contracts. No vendor inference/tracker implementation import. Guardian performs geometry. No risk/corridor/trajectory/alerts/cloud.

## D. WorldState contract

Immutable schema1: session/time, camera/entities/surfaces, quality, source ages, source status, capability status, provenance and bounded diagnostics. Frame recording schema6; recording remains opt-in.

## E. WorldEntity contract

Distinct WorldEntityId, TrackId reference, category, lifecycle, observed/predicted state, latest observed age, image geometry, depth/point/motion/semantic evidence, compact history and reasons.

## F. WorldSurfaceState contract

Latest bounded image-space regions/counts and exact source evidence. No dense masks retained. Optional supplied-plane projection delegates to Guardian and preserves UNVERIFIED status; real footage has no calibrated assumption. Analytical candidate (1,2,8)m passes, alongside zero center bearing. Richer projected polygons are deferred.

## G. Asynchronous input model

Independent typed ingest methods and frame-driven consume/snapshot interface. Per-source watermarks; no event queue. Late independent events within configured window accepted subject to exact object joins; duplicates/older same-source events rejected.

## H. Source freshness / age

Explicit source PTS age separate from process latency; defaults ordinary 500 ms, semantic 1,000 ms, allowed lateness 1,000 ms, retention 5,000 ms. These are configurable research policies, not safety thresholds.

## I. Entity identity mapping

Current retained TrackId maps one-to-one to a separately allocated WorldEntityId. IDs are monotonic within model lifetime; reset clears state without reusing serials.

## J. Track-ID-switch handling

Conservative false split. New ID at same geometry never inherits another entity history/depth. Expired IDs reappearing obtain new world identities. Real identity continuity remains imperfect.

## K. Depth fusion

Selected exact TrackDepthObservation only. Predicted tracks cannot create fresh depth samples. Old estimates retain source time and stale status; relative evidence stays nonmetric.

## L. Camera-space position

Analytical fixture produced (0,0,5)m from synthetic metric CAMERA_Z depth and valid calibration. UNKNOWN/invalid calibration and relative depth do not yield candidate metric positions.

## M. World-space position

Exact supplied pose/extrinsics produced analytical (1,2,5)m. Mismatched/stale/unreliable pose yields no current world point. Real footage has no supplied pose, so no metric localization claim.

## N. Image-motion evidence

Original pair, pixel displacement/rate, compensation and quality retained with explicit flow/ego provenance. No physical velocity is created.

## O. Semantic evidence

Class summary and optional exact-frame center consistency use generic SemanticFrame. Surface summaries consume generic SurfaceEvidenceFrame. Category disagreement is diagnosed; track category wins.

## P. Unverified semantic handling

Every semantic/surface/entity semantic contribution remains UNVERIFIED. All 96 Task010 review pages remain draft. No ground-truth scoring performed.

## Q. Surface state

Bounded original-camera boxes/area/bottom-connected metadata, flag counts, source provenance and age. Propagated versus observed status preserved; failures do not refresh payload time; retention removes old regions.

## R. Quality / capability model

Tracking, metric estimate, camera pose, semantic surface and motion capabilities have independent status/reasons. Conservative scene DEGRADED/UNRELIABLE; no confidence averaging or safety probability.

## S. Conflict handling

Bounded diagnostic codes for category disagreement, source failure, late/duplicate/older input, frame mismatch, pose/depth mismatch and caps. No automatic provider averaging, re-identification or second smoother.

## T. Partial pipeline results

Unit fixtures cover zero inputs and optional components. Actual YOLOX replay omits depth, semantics and flow, uses intermittent 1 Hz detection, and retains predicted tracks. YOLOX produced 90 snapshots, zero failures and peak 16 entities.

## U. Failure-injection results

Depth/segmentation recoverable pipeline failures and detector/pose/ego failure events retain coherent partial state. Tests assert original payload times/ages survive failure and expired payloads are discarded.

## V. Async input results

t0 observed track/depth, later prediction and later observed track retain exact depth age and STALE state. Duplicate and out-of-order events do not duplicate history. Session/source/future/time-reversal violations reject.

## W. Full first-person replay

All-real stack: PicoDet, relative Depth Anything, LK/visual ego adapter, PIDNet, tracking and world model. Three-second offline run: 90 processed/world states, zero failures, peak 54 entities, 778 history entries, 7 surface regions. Ten-minute REALTIME run: 604.52s wall time, 18,001 decoded, 18,000 admitted, 68 processed/world states, 17,933 dropped including end-boundary handling, zero failures. 67 semantic results were published by perception but all were beyond the world lateness policy; no surfaces were incorporated in this long run. Flow/ego pair gaps also prevent useful motion estimates. Thus the long run verifies bounded degradation, not practical realtime full-stack operation; the offline run separately exercises incorporated surface evidence. No validated calibration/pose or physical accuracy claim. Shared-machine concurrent stress/offline/tests affected timings.

## X. World model latency P50/P90/P95/P99

Long-run instrumented consume P50/P90/P95/P99: 2.735/4.444/4.788/6.479ms. Short offline snapshot P50/P90/P95/P99: 3.465/4.787/5.374/10.806ms. Stage-specific and source-age distributions are in the JSON. Timing windows are bounded 2,048; consume includes benchmark RSS/counter overhead. These are not sensor-to-publication guarantees.

## Y. Memory / long-run stability

Long replay: 1,314 entities created, 1,275 expired, peak 43 retained entities and 43 history entries; every state partial. Large inference gaps cause expiry between many updates. RSS start/peak/end 127,127,552/756,490,240/738,938,880 bytes; start is before loading model adapters, so the increase includes model allocation. Region peak 0 in long run, 7 in incorporated offline run. Synthetic runs separately exercise full history capacity. No retained dense histories; finite soak is not universal leak proof.

## Z. Many-entity stress test

2,000 updates for each load; ceiling 128. 1 inputs → 1 retained, history peak 16, update/snapshot P95 0.016/0.048ms; 10 inputs → 10 retained, history peak 160, update/snapshot P95 0.078/0.122ms; 50 inputs → 50 retained, history peak 800, update/snapshot P95 1.502/2.185ms; 100 inputs → 100 retained, history peak 1600, update/snapshot P95 3.217/4.552ms; 129 inputs → 128 retained, history peak 2048, update/snapshot P95 3.877/6.049ms. Input construction excluded from measured update/snapshot cost. These runs predate optional supplied-ground/bearing additions; those are disabled without geometry and do not affect this synthetic load.

## AA. Detector swap

Actual PicoDet full replay and YOLOX partial replay use the same WorldModel. Provider names/hashes remain in provenance.

## AB. Tracker swap

Alternate TrackSet fixture provenance accepted without world changes. Identity switch and replacement tests cover conservative mapping; no tracker internals consumed.

## AC. Depth swap

Two synthetic provider identities accepted through same TrackDepthObservation contract. Real relative Depth Anything used in replay; no new physical depth qualification.

## AD. Flow/ego swap

Two alternative provenance fixtures retain generic pair, scale and residual image-rate contracts. LK/visual adapter in real replay; absent motion supported. No new physical accuracy claim.

## AE. Segmenter swap

Generic fixtures with alternate provenance preserve UNVERIFIED state. PIDNet actual replay; PP-LiteSeg was measured in Task010, not requalified as ground truth here.

## AF. World-model replaceability

WorldModel protocol with injected alternate delegating implementation tested through Pipeline; consumers receive same WorldState schema1.

## AG. Task001–011 integration audit

See docs/architecture/TASK001_011_INTEGRATION_AUDIT.md for each boundary PASS/PARTIAL. All required implemented software joins pass; physical qualification and production remain partial; optional supplied-ground projection passes analytical tests but lacks real inputs.

## AH. Component replacement audit

Updated COMPONENT_REPLACEMENT_CONTRACTS.md. No vendor branches in world model; adapters own inference. Snapshot contract independent of prototype implementation.

## AI. Future Task012 contract

WorldState.camera_state, entity geometry, surface summaries and evidence/capability status. Corridor/free-space decisions not implemented; Task012 has not started.

## AJ. Future Task013 contract

Bounded timestamped observed/predicted history with compact depth and camera points. No future trajectories or physical-velocity estimator added.

## AK. Future Task015 risk contract

Explicit source time, freshness, prediction/propagation, source quality, validation status and reason codes. Non-null estimates do not imply calibrated reliability.

## AL. R&D experiments

20 RND-WM questions with rationale, hypothesis, experiment, metrics, criterion and honest status in docs/research/world-model-experiments.md.

## AM. Privacy / security

Local-only, existing dependencies, no raw footage export/cloud upload/biometric identity. Public configs omit paths. Debug state recording opt-in; identities are session objects only. Prior 5 reviewed development advisory entries remain.

## AN. Adversarial audit

No outstanding CRITICAL/HIGH identified after corrections and regression tests. HIGH fixes: failure/payload retimestamping, retention based on failure ticks, failure-status translation, late-depth source regression and UNKNOWN-calibration point publication. MEDIUM: provisional freshness, inherited tracking/depth/semantic quality, CPU contention/checkpoint rights. LOW: richer projected region geometry and polygon representation. See TASK011_AUDIT.md.

## AO. Test counts

558 tests passed in the final repository verification: 189 Guardian core, 342 perception-lab (including 47 new world-model cases), 24 web and 3 API tests.

## AP. Full verification

`npm run verify` completed with exit code 0 on 2026-10-21, recorded in `benchmark-results/task011-final-verify-v2.log`. Environment checks, formatting, linting, static analysis, unit tests, builds, dependency advisory review and runtime smoke checks passed. Smoke checks covered API contracts, the production web home page, eight concurrent health requests and API outage handling. Five previously reviewed development advisory entries remain; this is not a zero-vulnerability result. The first final run exposed an UNKNOWN-calibration point-publication bug; the corrected boundary and its regression test passed in this second run. No hosted CI/cloud/mobile verification claimed. Documentation closeout: 2026-10-22.

## AQ. Remaining risks

Human semantic ground truth deferred, metric depth and physical motion unvalidated, track fragmentation, calibration/pose unavailable on real footage, native runtime contention, model/checkpoint rights unresolved. No production safety or global localization claim.

## AR. Final verdict

TASK011 COMPLETE: YES — local prototype engineering scope. ENGINEERING QUALIFIED FOR TASK012: YES — prototype development with the documented limitations. WORLD_STATE_PRODUCTION_VALIDATED: NO. PHYSICAL_MOTION_VALIDATED: NO. SEMANTIC_GROUND_TRUTH_VALIDATED: NO. PRODUCTION_SAFETY_VALIDATED: NO. Full-stack CPU throughput remains insufficient for practical real-time use; the ten-minute replay establishes bounded degradation, not real-time qualification. Task012 has not started.

Measurement revision note: long replay predates the final edge-case guards and optional supplied-plane/bearing adapter. Those guards cover late object-depth failure metadata and metric estimate versus calibrated-position availability. Those paths are regression-tested separately; the real footage calibration is UNKNOWN and no ground plane/pose is supplied.
