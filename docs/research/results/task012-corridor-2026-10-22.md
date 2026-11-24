# Task012 — corridor and free-space evidence

Date: 2026-10-22. Scope: LOCAL_PROTOTYPE_ENGINEERING. Measurements are observations on this Windows machine, not production guarantees. Task013 has not started.

## A. Pre-task audit

Read-only inspection confirmed WorldState timing, entity/source ages, supported-only metric/world points, semantic UNVERIFIED status and Guardian geometry ownership. Independent image dimensions and localized compact surface evidence were missing; additive optional metadata resolves these joins. The first verification attempt reached 252 passing lab tests but 90 sandbox temporary-directory setup errors; it was not a passed baseline. The Task011 historical baseline remains 558 tests. See `docs/corridor/TASK012_AUDIT.md` for development failures and fixes.

## B. Files changed

New implementation: `corridor.py`, `corridor_types.py`, `corridor_config.py`, `corridor_overlay.py` in the perception lab; `CorridorGeometry.java` in Guardian. New tests: `test_corridor.py`, `CorridorGeometryTest.java`. Integration changes: world types/model, geometry bridge, LabConfig, FrameResult, pipeline, metrics, recording and optional visualization. Tools: corridor benchmark, optional hooks in world benchmark, lab check list and Windows generated-directory preparation in `tools/api.mjs`. Added corridor example config, eight corridor docs, research questions, integration audit and this report/JSON. Updated README/runtime/replacement/world-contract docs. Pre-existing Task009–011 edits were preserved; no commit or Task013 work was performed.

## C. Corridor architecture

Stateless `CorridorAnalyzer.analyze(WorldState)` produces immutable CorridorAnalysis. No polling, worker, history queue, model runtime import or new dependency. Guardian owns metric math; Python owns evidence selection and image heuristics.

## D. UserCorridor contract

UserCorridorState/UserCorridor carries state timestamp, InteractionZone, mode/frame, compact polygon, optional metric origin/basis/dimensions, heading and ground EvidenceSource, quality/reasons and nullable observed fraction. Source metadata is preserved, not replaced by processing time.

## E. Corridor modes

IMAGE_SPACE_CORRIDOR, GROUND_PLANE_CORRIDOR in camera coordinates, and WORLD_SPACE_CORRIDOR in session-local coordinates. AUTO selects a supported metric mode; invalid/missing support falls back explicitly. IMAGE forces the image heuristic.

## F. Heading source

CAMERA_FORWARD or POSE_CAMERA_FORWARD, with original identity, age, status and quality. Camera optical heading is not validated torso heading, walking velocity or intention. Future body-heading adapters are documented, not fabricated.

## G. Image-space fallback

Configurable centered lower-image trapezoid. Operates without metric calibration, depth, pose, ground plane, semantics or flow. No metric width/distance claim. Missing image dimensions produce UNAVAILABLE rather than guessed coordinates.

## H. Ground-plane / world corridor

Four-vertex tapered plane-aligned geometry uses Guardian vectors/transforms. Exact source-bound supplied ground and calibrated geometry are required; LOCAL_WORLD also requires matching current pose/extrinsics. Ground remains a supplied assumption. Projection clips valid vertices to image bounds and conservatively rejects near-plane crossings; unseen physical space is unknown.

## I. Entity representative point

Supported current metric object-depth point for explicitly assumed grounded categories (person, bicycle, motorcycle, car, bus, truck), otherwise visual bbox bottom-center/overlap. Neither is advertised as full physical footprint or actual ground contact; the metric branch records GROUNDED_CLASS_ASSUMPTION and HEIGHT_NOT_TESTED. Unknown/non-grounded categories fall back to image evidence. No generic class widths or blind ground projection of arbitrary detections.

## J. Entity-corridor relation

Every bounded entity receives INSIDE / INTERSECTS / NEAR_BOUNDARY / OUTSIDE / UNKNOWN, source evidence, quality, representative type and optional forward/lateral/signed-distance values. Source clocks, frame and freshness are checked. No outside entity is deleted.

## K. Inside / boundary / outside results

Analytical rectangle with near=1 m, far=5 m and half width=1 m: (lateral 0, forward 3) is INSIDE with signed distance -1 m; (1,3) is NEAR_BOUNDARY with distance 0; (+/-2,3) is OUTSIDE with distance +1 m; before-near and beyond-far are OUTSIDE. Rotated/tapered tests verify frame convention and width interpolation. These are geometric results, not hazards.

## L. Surface evidence integration

At most 768 regular image point samples of existing SurfaceFlag bits are retained in WorldState. Vectorized polygon selection yields sampled candidate-ground/traversable/obstacle/unknown fractions. Exact current frame/image alignment is required; stale unregistered masks yield unknown. Fractions are not exact area coverage or probabilities.

## M. Free-space evidence

UNKNOWN is always present for unseen/occluded physical space; AVAILABLE_EVIDENCE and OCCUPIED_EVIDENCE may coexist. Occupied entity IDs and semantic obstacle samples are evidence only. No occupancy map, safe path, route, warning or guaranteed-free state.

## N. Unknown-space handling

Absent/unusable samples yield unknown fraction 1 and null candidate fractions. Unsupported zero flags also count unknown. Labeled visible samples do not remove unknown physical volume behind objects. Tests cover mixed known/unknown/obstacle samples and empty scenes.

## O. Unverified semantic handling

All derived semantic coverage remains UNVERIFIED. All 96 Task010 review pages remain DRAFT/UNVERIFIED; no human validation has been marked complete.

## P. Depth-free results

The actual YOLOX partial replay, with no depth/semantics/flow, produced 90 analyses with no processing failure. Relative-depth fixtures never publish metric relation offsets.

## Q. Semantic-free results

Image/entity geometry remains available. Surface evidence is UNAVAILABLE with unknown fraction 1. This is explicitly exercised by partial replay and tests.

## R. Calibration-free results

All 482 long-run analyses used IMAGE_SPACE_CORRIDOR with DEGRADED quality. The real footage has UNKNOWN physical calibration and no supplied plane/pose; it does not qualify metric operation.

## S. Rapid-turn results

Synthetic pose rotations (0, 0.1, 1.57, 3.14 and -1.57 radians) yield the expected finite current camera-forward basis. An older semantic mask is rejected even within the generic freshness window. Real body-heading/rapid-turn accuracy is unvalidated.

## T. Crowd results

Synthetic stress preserves all 1/10/50/100/128/512 input entities with O(N) relations. This establishes bounded compute, not crowd identity/relevance accuracy; tracking fragmentation remains inherited.

## U. First-person replay results

Same source SHA256 as Task011: `e011aa64a65aa9aeb00fce657312362742d12dfd9170f76878e2a784ab1fc5e2`.

| Run                                      | Source duration | Wall time | Analyses | Processing failures |
| ---------------------------------------- | --------------- | --------- | -------- | ------------------- |
| Full realtime                            | 600 s           | 600.600 s | 482      | 0                   |
| Full offline with bounded debug overlays | 3 s             | 7.944 s   | 90       | 0                   |
| YOLOX partial offline                    | 3 s             | 1.228 s   | 90       | 0                   |

Full stack uses existing PicoDet, tracking, relative Depth Anything, LK/visual motion, PIDNet and world model. No new model. Two of eight local debug PNGs were visually inspected: central vehicle representatives lie inside the image polygon, side objects remain annotated, and old semantic samples become unknown. This is an automated-assistant engineering spot-check, not human truth review. Reviewed per-scenario coverage for campus, sidewalk, road edge, crowd, parked obstacles, turns, high camera motion and mixed scenes is incomplete; do not claim independent qualification of those strata.

## V. Corridor latency P50/P90/P95/P99

Milliseconds, direct analyzer timer excluding benchmark instrumentation:

| Run                       | P50    | P90    | P95    | P99    | Max    |
| ------------------------- | ------ | ------ | ------ | ------ | ------ |
| 600 s integrated realtime | 0.2022 | 0.3382 | 0.3901 | 0.5914 | 0.7654 |
| 3 s full offline          | 0.3805 | 0.8491 | 0.9075 | 1.6128 | 1.6128 |
| 3 s YOLOX partial         | 0.1092 | 0.1664 | 0.1935 | 0.4655 | 0.4655 |

These real runs exercise image fallback. Metric geometry is analytically tested; production metric performance is not separately qualified.

## W. Full-pipeline update rate

482/600 = 0.8033 updates per source second (0.8025 per wall second), versus Task011's historical 68/600 = 0.1133. 18,001 frames decoded, 18,000 admitted, 482 processed, 17,519 dropped (including end-boundary handling). This is still far below wearable realtime. World-update interval P50/P95/P99 was 1.20/1.60/1.933 seconds.

## X. Task012 throughput overhead

Mean corridor compute was 0.2178 ms, approximately 0.0175% of the 600.600 s replay wall time in aggregate. No material Task012 slowdown was observed. The Task011/012 measurements are not paired controlled experiments: concurrent machine load and runtime conditions differ, so the upstream speedup cannot be attributed to corridor code. The major bottleneck remains upstream inference cadence.

## Y. Memory / long-run stability

Zero processing failures; 482 image-mode analyses, zero mode switches, 482 DEGRADED results. Process RSS: start 126,078,976 bytes (before model load), sampled peak 757,264,384, end 721,530,880. Samples include model/JVM/native allocations, not just Task012. The analyzer is stateless; sample and entity caps are explicit. This bounded ten-minute observation is not a universal leak proof. Image polygon stability is by construction for fixed dimensions, not validation of alignment with human walking direction.

## Z. Many-entity stress results

2000 analyses per count, isolated immutable-snapshot compute timer; shared-machine conditions:

| Entities                    | P95 ms |
| --------------------------- | ------ |
| 1                           | 0.0208 |
| 10                          | 0.0987 |
| 50                          | 0.5444 |
| 100                         | 0.9725 |
| 128 (default world cap)     | 1.2478 |
| 512 (maximum supported cap) | 5.0171 |

512-entity P50 was 3.1884 ms and P99 6.4009 ms; do not assume the maximum cap meets a sub-millisecond budget. No pairwise scan or video-duration growth occurs.

## AA. Component swap test

Actual PicoDet full and YOLOX partial paths feed the same analyzer unchanged. Synthetic alternate tracker/depth/semantic provenance fixtures preserve the contract. Flow/ego remain optional upstream WorldState evidence; Task012 imports no implementations. Replacing providers does not improve their validation status.

## AB. World-model replacement test

An alternative WorldState producer/provenance and an injected alternative analyzer pass identical relation/recording contracts. Tests compare actual outputs and retain all entities, rather than merely constructing a protocol object.

## AC. Task001–012 integration audit

PASS: 001→002, 002→003, 003→004, 004→005, 005→006, 006→007, 007→008, 008→009, 009→010, 010→011, 011→012, 003→012 geometry, 004→012 heading/pose, 007→012 image geometry, 008→012 metric candidate, 010→012 surface evidence. PARTIAL: independent scenario coverage, physical/safety qualification and production runtime. No FAIL software boundary remains identified. Details: `docs/architecture/TASK001_012_INTEGRATION_AUDIT.md`.

## AD. Component replacement audit

Updated `COMPONENT_REPLACEMENT_CONTRACTS.md`. No detector/tracker/depth/flow/ego/segmenter/WorldModel implementation import in the analyzer. CorridorAnalyzer itself is replaceable behind CorridorAnalysis. No new framework/dependency.

## AE. Future Task013 contract

Matching-session/time `(WorldState, CorridorAnalysis)`: entity IDs, complete entity set/history, relation, optional metric basis/offsets, image polygon and source/quality/unknown status. Trajectory prediction is not implemented.

## AF. Future Task014 contract

Optional geometric corridor basis and current relation evidence; TTC/CPA require future sufficiently supported physical trajectories. No collision inference is performed here.

## AG. Future Task015 contract

Risk/attention can consume geometric relevance, occupancy evidence and explicit unknown/freshness/validation. Task012 does not suppress outside objects or assign risk priority.

## AH. R&D experiments

20 structured RND-COR questions are documented with WHY, HYPOTHESIS, EXPERIMENT, METRICS, DECISION CRITERION and STATUS in `docs/research/corridor-experiments.md`. Planned utility/body-heading/independent validation studies are not presented as executed results.

## AI. Privacy / security

No cloud upload, telemetry, new endpoint, credentials, faces/identity processing or global location map. Raw footage and eight debug PNGs remain local and Git-ignored. Public measurement exports omit private paths/images. Existing dependency review still includes five reviewed development advisory entries; no zero-vulnerability claim.

## AJ. Adversarial audit

CRITICAL: none outstanding identified. HIGH: none outstanding identified after exact surface-alignment guards, temporal/frame gates, invalid-ground JNI exception translation and calibrated-current metric point checks. MEDIUM: body-heading proxy, sparse semantics, tracking fragmentation, physical accuracy, independent scenario coverage and upstream cadence. LOW: richer footprint/occlusion and distorted-edge visualization. See the dedicated audit for scope and evidence.

## AK. Test counts

616 tests passed in the final full repository run: 192 Guardian, 397 perception-lab (including 55 corridor cases), 24 web and 3 API. Task012 adds 58 tests over the Task011 total of 558: 55 Python corridor cases and three Guardian analytical geometry tests.

## AL. Full verification

Final `npm run verify` completed with exit code 0 on 2026-10-22; evidence is `benchmark-results/task012-final-verify-v3.log`. Environment checks, Prettier, Ruff, strict mypy (62 source files), ESLint, strict TypeScript, Spotless, SpotBugs, all 616 tests, production builds, dependency review and runtime smoke passed. Smoke covered API contracts, the production home page, eight concurrent health requests and API outage handling. Five reviewed development advisory entries remain; no unreviewed advisory was reported.

Initial final attempt failed Maven clean because OneDrive restored READONLY on generated directories. The fixed Windows core-check preparation clears that attribute only within the fixed generated target, rejects linked directories and leaves sources untouched. A subsequent full run passed; a sandboxed follow-up lab run using workspace-local temporary files then failed one recorder-finalization test. The final full run used a fresh system temporary directory outside OneDrive with elevated execution and passed every test, including that case. This demonstrates the successful verification environment, not a guarantee that arbitrary synced filesystems cannot deny writes. No hosted CI, cloud deployment, mobile runtime, physical wearable, human semantic review or production safety verification is claimed.

## AM. Remaining risks

Real footage has unknown calibration, relative depth and no supplied pose/plane. Full realtime coverage remains sparse; all eight bounded diagnostic examples in the long run had no aligned current surface samples (unknown=1). They do not establish the run-wide surface-coverage distribution. Offline overlays demonstrate sampled evidence when aligned. Mask/physical/corridor accuracy and all requested independently reviewed scenario strata remain unqualified. Camera heading need not equal user motion; strong distortion/occlusion and exact area coverage need further research. Hardware load/checkpoint rights and five reviewed development advisories remain inherited concerns.

Measurement revision note: the ten-minute run preceded final additional metric-point guards and invalid-ground Java exception translation. Its UNKNOWN-calibration image fallback never enters those paths; the final metric/degenerate cases are separately regression-tested. No source/runtime performance improvement is claimed from those changes.

## AN. Final verdict

TASK012 COMPLETE: YES — local prototype engineering scope.

ENGINEERING QUALIFIED FOR TASK013: YES — prototype development with the documented evidence and performance limitations.

SAFE_PATH_VALIDATED: NO.

FREE_SPACE_SAFETY_VALIDATED: NO.

PRODUCTION_SAFETY_VALIDATED: NO.

Task013 has not started.
