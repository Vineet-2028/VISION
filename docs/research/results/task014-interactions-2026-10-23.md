# Sentinel Task 014 â€” local prototype/research completion report

Date:2026-10-23. Executed evidence and limits; no physical/safety qualification.

**Key limitation:** the tracker-proxy evaluation found only 3 of 52 entry events (5.8% recall). Software completion does not establish reliable real-world forecasting.

## A. PRE-TASK AUDIT

Read Guardian TTC/CPA code/tests, Task 013 contracts/results, world/corridor/depth/pose validity, clock rules, bridge ownership, scheduler, recording and replacement documents before implementation. The future-only CPA API intentionally omitted past times. An additive signed-time query was needed. The first baseline process lost its exit status; retry exited 0 but overlapped initial additions, so it is intermediate evidence, not a pristine baseline.

## B. FILES CHANGED

Added interaction_config/types/geometry/motion/analyzer/overlay modules, test_interaction.py, tools/interaction_benchmark.py, an example config, ten interaction docs, research register and this report. Extended Guardian Motion and its test, typed JPype adapter, optional Pipeline/config/contracts/metrics, recording schema 9, visualization, replay injection, checked-tool list and READMEs. Existing Tasks 009â€“013 uncommitted work is preserved. No new production dependency or Task 015 code.

## C. INTERACTION ARCHITECTURE

IMPLEMENTED stateless O(NÃ—HÃ—polygon_edges) consumer after Task 013, with 512 entities,2048 hypotheses,8 horizons,16 polygon vertices and 3 s bounds. No worker, inference, entity-pair graph, session-long history or wall-clock evidence. Each hypothesis retains its own identity; hypotheses are not independent votes.

## D. INTERACTIONANALYSIS CONTRACT

Immutable session/source timestamp, per-hypothesis entity forecasts, world/corridor/trajectory/config provenance, quality summary, bounded diagnostics and unavailable reasons. Schema 1. Matching source time/session/schema/provenance required.

## E. ENTITYINTERACTIONFORECAST CONTRACT

Retains current/future relation, entry/exit/intervals, envelope class, closest corridor approach, approach evidence, compact samples, optional TTC/CPA candidates, source ages, validity, assumptions, provenance, direction and reference. No risk score, alert or collision verdict.

## F. INTERACTION EVIDENCE LEVELS

IMAGE_GEOMETRIC, BEARING_GEOMETRIC and WORLD_RESEARCH_UNVALIDATED implemented. PHYSICAL_METRIC_VALIDATED reserved and never emitted. Quality propagates pessimistically and does not alter physical validity.

## G. CORRIDOR ENTRY / EXIT

Convex piecewise segment clipping finds intersections between samples, exit and re-entry without extending Task 013 horizons. Same-side returns are PREDICTED_ENTER_EXIT; opposite lateral traversal is CROSS_CORRIDOR. Final-horizon exit remains unresolved.

## H. TRAJECTORY ENVELOPE INTERACTION

NOMINAL_INTERSECTION, conservative POSSIBLE_INTERSECTION, NO_INTERSECTION_WITHIN_ENVELOPE and UNKNOWN are distinct. Maximum adjacent radius bounds each swept segment. This is uncalibrated geometry, not probability. Exact earliest/latest possible entry windows remain unavailable.

## I. CLOSEST CORRIDOR APPROACH

Minimum unsigned region distance and earliest minimizing horizon across all segments. Pixels remain pixels. Matching world corridors use ground-plane projection in research meters, explicitly not 3 D clearance or object-user CPA.

## J. APPROACH / RECEDING EVIDENCE

Endpoint distance trend to the frozen corridor is geometric approach/recession; approach then return can be indeterminate. Bearing evidence references camera-forward angle, not range. Metric closing speed only comes from Guardian research-relative motion. Static inside entities remain represented.

## K. TTC INTEGRATION

CoreGeometry.relative_motion invokes Guardian relativePosition, relativeVelocity, closingSpeed and radialTtc. Positive closing speed approaches; no production TTC formula exists in Python. Finite radial TTC is not collision proof.

## L. TTC EDGE CASES

Tested non-closing, lateral, stationary, near-zero separation, invalid units, missing reference, disabled research, relative depth rejection and outside-horizon flags. No Infinity sentinel or negative TTC. Missing/unknown velocity cannot become a physical estimate.

## M. CPA INTEGRATION

Guardian owns both future closestApproach and additive signedClosestApproachSeconds. The existing future-only API reuses signed math and retains its old behavior. Python delegates and assigns explicit statuses.

## N. CPA EDGE CASES

Past CPA retains signed time; zero relative velocity has undefined time and separate current separation. Lateral/head-on/side-pass tests pass. Mathematical values beyond supplied horizon remain flagged, not extrapolated near-term evidence.

## O. USER-MOTION LIMITATION

Validated user physical velocity is absent. Real moving-user physical TTC/CPA is therefore unavailable; image interactions do not assume a stationary user.

## P. STATIC-USER RESEARCH REFERENCE

research_metric and static_user_reference are opt-in. Current supplied device/world origin with assumed zero velocity is labeled STATIC_USER_ASSUMPTION and RESEARCH_ONLY. Provided moving references also retain unvalidated object-motion status.

## Q. PHYSICAL VALIDITY PROPAGATION

Compatible depth kind, pose/frame/time/calibration, source freshness, trajectory velocity status and reference units are gated. Relative depth cannot produce metric TTC/CPA. A producer string cannot promote evidence to physically validated.

## R. TTC VS CORRIDOR-ENTRY DISTINCTION

Separate fields, statuses and tests: a synthetic head-on point at(0,4)m with velocity(0,-2)m/s has corridor entry 0.5 s but radial TTC2 s. Entry is not time to the user.

## S. TTC / CPA VS TRAJECTORY DISAGREEMENT

Bounded diagnostics preserve finite TTC with no corridor intersection and corridor intersection with unavailable TTC. Future risk consumers receive the disagreement; Task 014 does not resolve it into danger.

## T. SYNTHETIC HEAD-ON RESULTS

Actual Guardian bridge: r=(0,10,0), v=(0,-2,0) gives closing 2 m/s, TTC5 s, CPA5 s/0 m. The configured 3 s horizon marks those times outside prediction horizon. Integrated shorter case above gives 2 s with exact corridor geometry. Mathematics only.

## U. SYNTHETIC SIDE-PASS RESULTS

Guardian r=(2,10,0), v=(0,-2,0) gives radial TTC5.2 s and CPA5 s/2 m. Integrated(2,4,0) case has finite research TTC,2 mCPA and no corridor crossing. No collision classification.

## V. SYNTHETIC CROSSING RESULTS

Image square[0,2]Ã—[0,2], point(-1,1), velocity(2,0): entry 0.5 s, exit 1.5 s, minimum 0 px. Reverse crossing direction also verified. Piecewise same-side return enters 0.125 s/exits 0.375 s, proving chord-only calculation would be wrong.

## W. STATIC-OBSTACLE RESULTS

Static inside image point remains inside with no fabricated TTC. Static research-world point produces NON_CLOSING TTC and ZERO_RELATIVE_VELOCITY CPA with current estimated separation retained.

## X. REAL CORRIDOR-ENTRY EVALUATION

MEASURED15 s source,450 processed frames, zero failures,119.6 s wall. Frozen prediction-time polygon; future observed same-ID bottom centers. Events:{'FN': 49, 'TN': 48, 'FP': 1, 'TP': 3}; eligible windows:101; censored:194; end-pending:69; overflow:0. Precision:0.75; recall:0.06; matched entry MAE:0.20 s; minimum-distance MAE:134.07 px. These are tracker proxies, not independently reviewed events. Current truth starts at observed boxes. The initial 150 ms gap rule was incompatible with 200 ms detector cadence; its fully censored run is preserved and excluded.

## Y. PEDESTRIAN CROSSING RESULTS

UNVALIDATED independent scenario accuracy. Person-class hypotheses occur in the development replay; class counts do not establish reviewed crossing events. Synthetic crossing geometry passes. No fabricated per-class precision.

## Z. BICYCLE / MOTORCYCLE RESULTS

UNVALIDATED independent scenario accuracy. Local overlays show urban road traffic; labels and identities are model outputs. Bicycle/motorcycle-specific timing qualification needs reviewed held-out events.

## AA. PARALLEL VEHICLE RESULTS

Analytical parallel-outside fixture preserves non-entry and known minimum distance. Real vehicle class occurrences are recorded, but parallel motion is not independently annotated.

## AB. HIGH-MOTION RESULTS

Image motion never becomes physical closing speed; upstream quality/research limits persist. Independently labeled camera-turn/body-motion strata remain unavailable.

## AC. CROWD RESULTS

Development replay recorded 142 identity disappearances; these are not an independently labeled fragmentation rate. No retained interaction history transfers between IDs. Crowded-scene physical/event qualification remains unvalidated.

## AD. SMALL-OBJECT RESULTS

Uncertainty/robust-trajectory contracts are retained; small-object event jitter is not independently measured in a reviewed stratum. Planned held-out evaluation, not a fabricated success.

## AE. PHYSICAL TTC VALIDATION STATUS

NO. Synthetic equation/bridge correctness only; no measured real object/user motion reference.

## AF. PHYSICAL CPA VALIDATION STATUS

NO. No independent real metric miss-distance/relative-velocity ground truth.

## AG. TASK014 LATENCY P50/P90/P95/P99

Long replay compute:4.76/14.27/15.80/18.25 ms; max 18.25 ms. Dense offline replay:11.35/19.51/21.16/25.64 ms. Counts and distributions are in JSON. Bridge microbenchmarks and sampled serialization are separately recorded; file-I/O cost and upstream waiting are not claimed as geometry compute.

## AH. MANY-ENTITY STRESS

MEASURED200 calls per entity count, fixed six horizons. See table below. Large-count tails exceed the few-ms target; no hard real-time or wearable guarantee. Whole-process RSS is not an isolated allocator/leak proof.

| Entities | P50 ms | P95 ms | P99 ms |
| -------- | -----: | -----: | -----: |
| 1        |   0.12 |   0.19 |   0.29 |
| 10       |   1.26 |   2.95 |   3.69 |
| 50       |   8.13 |  21.31 |  24.09 |
| 100      |  40.13 |  47.54 |  65.49 |
| 128      |  52.78 |  59.42 |  84.31 |
| 512      | 214.20 | 266.93 | 511.41 |

## AI. TEN-MINUTE REPLAY

Completed 600.0 s source in 601.4 s wall. World/corridor/trajectory/interaction counts:[85, 85, 85, 85]; failures 0. RSS start/peak/end:127844352/768397312/750706688 bytes. The earlier run recorded a 704 s frame-conversion pause and is excluded from throughput comparison; a temporary system-awake request was used and released for this retry.

## AJ. FULL-PIPELINE UPDATE RATE

85/600=0.142 source updates/s versus Task 013446/600=0.743. Historical difference-80.9%. This comparison is hardware/load-sensitive, not a controlled causal claim. Upstream perception remains the dominant bottleneck.

## AK. THROUGHPUT OVERHEAD

Measured interaction compute totals 0.525 s,0.087% of wall time. Stage timing additionally includes benchmark counters; serialization samples are separate. Historical rate differences cannot be attributed solely to this addition. No upstream bottleneck is hidden. Matched sequential 15-second offline runs processed 450 frames each with zero failures: baseline 116.51 s, interaction 118.14 s, wall-time change +1.40%. Evaluation and overlays were disabled in both. One pair cannot establish a statistically significant regression or a future performance guarantee.

## AL. INTERACTION ANALYZER SWAP TEST

PASS: an injected protocol-compatible wrapper is consumed by Pipeline, publishes expected counts and writes schema 9. Downstream consumes immutable contracts, not selected analyzer class.

## AM. PREDICTOR SWAP TEST

PASS: CP, last-twoCV, windowCV, adaptive and alternate piecewise paths feed the same analyzer. No predictor implementation import or inferred extension beyond supplied horizon.

## AN. COMPONENT REPLACEMENT AUDIT

Normalized world/corridor/trajectory inputs isolate detector/tracker/depth/flow/segmenter providers. Many-entity/alternate-identity fixtures and real PicoDet pipeline exercise contracts. Not every vendor model combination was rerun; provenance labels are not equivalent to physical/provider qualification.

## AO. TASK001-014 INTEGRATION AUDIT

See docs/architecture/TASK001_014_INTEGRATION_AUDIT.md for every boundary PASS/PARTIAL/FAIL. Sequential software compatibility and Guardian/time/world/trajectory integration PASS. Identity continuity, real depth/motion validity and moving/bearing-corridor representation remain PARTIAL research limits.

## AP. FUTURE USER-TRAJECTORY COMPATIBILITY

ReferenceMotion provides session/time/frame/position/velocity/units/quality/validation/provenance. A synchronized future UserTrajectory adapter can populate it. Stronger physical authorization and time-varying corridor implementation are future extensions; immutable output consumers need no equation rewrite.

## AQ. FUTURE TASK015 CONTRACT

WorldState+CorridorAnalysis+TrajectorySet+InteractionAnalysis with matching source identity. Risk policy may inspect geometry, validity, quality, unknowns and disagreements; it must not recompute TTC/corridor geometry or assume image entry is collision. Task 015 not implemented.

## AR. R&D EXPERIMENTS

Twenty-one entries in docs/research/interaction-experiments.md include question, motivation, hypothesis, experiment, metrics, criterion, status. Synthetic/runtime work is distinguished from planned independently reviewed scenario and physical-ground-truth studies.

## AS. PRIVACY / SECURITY

No new production dependencies, service, upload, telemetry, biometrics or cross-session identity. Local footage/PNG/raw benchmark artifacts remain ignored. Public results omit private source paths/images. Existing gate reports five reviewed development advisory entries, not zero vulnerabilities; no bypass added.

## AT. ADVERSARIAL AUDIT

CRITICAL/HIGH fixed: signed past CPA information, physical/unit/reference/source gates, stale trajectory suppression, correct piecewise entry/exit, explicit envelope/unknown state, same-side return distinction, benchmark renderer contract and observed-truth initialization. No outstanding Task 014 critical/high implementation defect identified after regression checks. MEDIUM: upstream cadence, tracker-reference bias, unvalidated physical sensing, large-count latency and unreviewed strata. LOW: debug density and unavailable exact possible-entry windows. Fixes/limitations are detailed in docs/interaction/TASK014_AUDIT.md.

## AU. TEST COUNTS

732 total: 193 Guardian + 512 perception-lab + 24 web + 3 API. Task 014 adds 66 Python cases and 1 Guardian test. Tests establish software behavior, not human or physical validation.

## AV. FULL VERIFICATION

PASS: npm run verify exit 0; Prettier, Ruff, strict mypy, ESLint, strict TypeScript, Spotless, SpotBugs, all tests, production builds, dependency gate and runtime smoke. Final diff/format checks recorded separately. Hosted CI, production deployment, mobile/hardware and independent human validation were not executed.

## AW. REMAINING RISKS

Image corridors are frozen heuristics, forecasts are point paths, envelopes are uncalibrated and track identity can change. Metric/user motion and semantic human review remain unvalidated. Long-horizon errors and system throughput prevent wearable safety claims. Five reviewed development advisory entries remain. No future-error-free or production-ready promise. The measured 5.8% entry recall is inadequate for safety use; held-out event annotation and upstream forecasting improvements remain required.

## AX. FINAL VERDICT

TASK014 COMPLETE: YES â€” local prototype/research engineering.

ENGINEERING QUALIFIED FOR TASK015: YES â€” with the explicit validity limits above.

CORRIDOR_INTERACTION_VALIDATED_FOR_PROTOTYPE: PARTIAL â€” deterministic geometry verified, real tracker-proxy evaluation only.

PHYSICAL_TTC_VALIDATED: NO.

PHYSICAL_CPA_VALIDATED: NO.

COLLISION_PREDICTION_VALIDATED: NO.

RISK_VALIDATED: NO.

PRODUCTION_SAFETY_VALIDATED: NO.

Task 015 not started.
