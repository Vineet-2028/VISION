# Sentinel Task013 — local prototype/research report

Date:2026-10-23. Complete for local prototype/research engineering; physical and safety validation remain unavailable.

## A. PRE-TASK AUDIT

Read Task012 report, WorldState/WorldEntity/EntityHistory, CorridorAnalysis, tracker prediction, depth joins, image residual motion, Guardian physical/temporal math, scheduler, recording and replacement contracts before implementation. Histories had timestamps and observed/predicted status; pixels were non-physical; metric depth unvalidated; no existing component owned downstream trajectory hypotheses. Guardian MotionPrediction already provided nominal physical math and is reused. The first verification attempt failed on generated pytest files in an untracked source directory; they were preserved in ignored benchmark-results/task012-generated-test-artifacts. A retry overlapped implementation and is not represented as a clean baseline.

## B. FILES CHANGED

Added six trajectory runtime modules (config, types, fit, predictor, corridor relation, overlay), test_trajectory.py, tools/trajectory_benchmark.py, a trajectory example config, nine trajectory documents, the research register and Task001–013 integration audit. Extended world history/source capture, Guardian Python bridge, config/contracts/pipeline/metrics/recording/visualization, world benchmark injection, checked-tool list and replacement/runtime READMEs. Updated apps/web/package.json and package-lock.json for Next.js16.4.2 plus docs/security.md. Pre-existing Task009–012 changes are preserved and are not claimed as new Task013 work. No Task014 implementation, deployment or Git commit was made.

## C. TRAJECTORY ARCHITECTURE

IMPLEMENTED: optional stateless TrajectoryPredictor.predict(WorldState, CorridorAnalysis|None). One derived immutable TrajectorySet per WorldState update; no new worker or model inference. Predictor uses normalized contracts, not detector/tracker/vendor classes. Output never feeds upstream observations. Fixed bounds:512 entities,32 fit observations,8 horizons,3 seconds. Existing world history remains bounded. Recording schema8 is opt-in.

## D. TRAJECTORY DOMAINS

IMAGE_SPACE: pixels and pixel/second. CAMERA_BEARING_SPACE: Guardian angles in radians and radian/second, locally extrapolated on the current angular branch. LOCAL_WORLD_RESEARCH: supplied local-frame metric candidates and research m/s. No silent unit conversion. Bearing/world may be unavailable while image trajectories remain available. Representation preference is world research > bearing > image, not a physical-accuracy ranking.

## E. PREDICTEDTRAJECTORY CONTRACT

Frozen records retain entity/trajectory identity, source-state and prediction-start nanoseconds, domain/frame/units, model, physical status, origin/velocity and validity, samples, envelope, quality/reasons, source FrameIdentities/count/span, rejected-count/residual, provenance and config hash. TrajectorySample retains horizon, timestamp, point, radius and quality. TrajectorySet also retains preferred IDs, unavailable diagnostics and optional corridor relations. Consumers must validate matching session/time and physical status.

## F. PHYSICAL VALIDITY MODEL

IMAGE_ONLY, CAMERA_RELATIVE, WORLD_RESEARCH_UNVALIDATED and reserved PHYSICAL_METRIC_VALIDATED are explicit. The final status is never emitted. World estimates always retain METRIC_DEPTH_UNVALIDATED and RESEARCH_METRIC_ESTIMATE. No physical user trajectory is fabricated.

## G. MODELS IMPLEMENTED

CONSTANT_POSITION, CV_LAST_TWO, CV_WINDOW and ADAPTIVE selection share the same output contract. An optional exact-frame compensated-flow hypothesis uses RESIDUAL_RATE_RESEARCH in a separately named stabilized-image frame. No learned model, intent, social interaction, map constraint or new dependency.

## H. CONSTANT POSITION RESULTS

Synthetic stationary CP ADE/FDE are0/0 pixels. Horizontal10px/s motion yields13.75/30 pixels across the six horizons; diagonal motion15.373/33.541. In real tracker-reference evaluation CP mean endpoint errors are96.192,133.027,222.984,306.603,375.761 and486.246 pixels from0.25 through3 seconds. Runtime CP may use a denoised stationary fit position when stable history exists; the synthetic CP comparison is the plain last-position baseline.

## I. CONSTANT VELOCITY RESULTS

Both CV baselines recover clean horizontal/vertical/diagonal and irregular-time linear fixtures to floating-point precision. Last-two CV is much worse under alternating jitter: synthetic ADE22.8/FDE48.8px. It is an experiment option, not the default. Real errors and matching counts are in sectionU.

## J. WINDOWED FIT RESULTS

PROVISIONAL primary uses median temporally separated pair slopes as a robust seed, rejects large residual observations, then fits inlier OLS. This replaces an initially expensive all-pairs seed; bounded seed work is linear in history length. Alternating image jitter yields ADE0.4/FDE0.706px versus last-two22.8/48.8. The isolated false-point fixture is rejected; newest-outlier tests prevent anchoring prediction on that rejected point. This does not guarantee resistance to majority-corrupted identities.

## K. CONSTANT ACCELERATION RESULTS / DECISION

CA explicitly DEFERRED. On synthetic acceleration, window CV ADE/FDE10.346/27.7px and last-two5.796/18.6 show the cost of a long linear window. These results expose CV limits; they do not qualify acceleration estimation. Noisy/fragmented observation histories and absent independently reviewed motion truth do not justify selecting another derivative by default.

## L. MODEL SELECTION POLICY

Default CV needs3 observations spanning100ms, no retained observation gap above500ms, and fit residual <=4 times the domain floor. Recent history is at most2 seconds/16 samples by default. Observed-only input; predicted tracker samples are excluded. Insufficient history falls back to CP. Small displacement selects stationary CP. Rejected outliers/high residual/weak or predicted input degrades quality. More than500ms since the latest usable observation yields no trajectory. No class-based speed prior.

## M. IMAGE-SPACE TRAJECTORY

IMPLEMENTED bbox bottom-center prediction in original image coordinates. Future points may leave the image; that is a prediction, not an observation or a metric route. Image motion includes camera motion. Histories are source/time/sequence/session checked; unknown clocks, future input, regression and mixed sources are not silently fitted.

## N. EGO-COMPENSATED TRAJECTORY

IMPLEMENTED alternate exact-frame hypothesis from Task009 residual rate with track/session/pair/calibration/image-size gates. It retains source identities and flow provenance, is always UNRELIABLE, is never preferred over raw representation, and is not treated as a raw future-camera point for corridor entry/overlay. Synthetic swap/gating tests execute this path. Real capture has unknown calibration, so no compensated hypothesis was available; real compensated accuracy is UNVERIFIED. A future stabilized-view reference is required for a fair comparison, not raw-view endpoint error.

## O. BEARING TRAJECTORY

IMPLEMENTED from Guardian-derived observed azimuth/elevation history, with calibration identity preserved per observation. Radian rates are non-physical. Large angular discontinuities reset the usable history. Tests verify Guardian integration and partial image/bearing availability. This is local angular extrapolation, not a validated direction or a guarantee the object remains in view.

## P. WORLD-SPACE RESEARCH TRAJECTORY

IMPLEMENTED only for exact metric-depth/pose joins in the same local frame and calibration. Optional world points/source provenance were added to EntityHistory. Both pose-first and depth-first capture routes use the same exact join. Current missing/stale pose or changed calibration disables this domain. Guardian MotionPrediction produces metric nominal samples. Synthetic x-motion tests preserve y/z; the three-axis benchmark uses x/y/z rates1/2/3. Real footage has no eligible physical world trajectory.

## Q. DEPTH / POSE QUALITY PROPAGATION

Relative depth, wrong calibration, unreliable/missing/stale pose, incomplete source joins and negative camera-forward points cannot produce world research trajectories. Each historical world candidate retains its depth and pose evidence and calibration ID. No latest-pose substitution and no up-to-scale translation silently treated as meters. World source provenance is carried downstream; physical validation remains NO.

## R. UNCERTAINTY ENVELOPE

IMPLEMENTED transparent scalar domain-unit radius based on floor, fit residual and source age, growing monotonically with horizon. Floors of 2px/0.01rad/0.25 research meters are experimental settings, not body dimensions. Unreliable input doubles the base; horizons beyond 1 second are UNRELIABLE. UNCALIBRATED research envelopes are not covariance/probability/coverage guarantees. Monotonicity and input immutability are tested.

## S. SYNTHETIC ADE/FDE RESULTS

MEASURED in synthetic-qualified.json: clean linear and irregular CV errors approximately zero; stationary all models0. Image jitter: CP12.95/29.2, last-two22.8/48.8, window0.4/0.706px. Outlier window0/0. Three-axis synthetic meters: CP5.145/11.225, CV variants approximately0; depth-jitter last-two5.7/12.2 versus window0.1/0.176. These validate nominal math only, not real sensor accuracy.

## T. REAL RETROSPECTIVE PREDICTION RESULTS

MEASURED15-second user-owned capture replay:450 processed updates, zero processing failures,116.495s wall time including full upstream work and evaluation instrumentation. Evaluator samples predictions every250ms and scores against every later observed same-WorldEntityId point within100ms after target. Zero queue overflow;23,596 unmatched/expired samples and4,484 end-censored pending samples across compared hypotheses. This is biased tracker-reference consistency, not independently reviewed accuracy. No future observation is used in fitting and past predictions never change. The first run overflowed and is excluded from model selection.

## U. HORIZON-BY-HORIZON RESULTS

Mean matched endpoint error in pixels; same matched counts for each model at each horizon. These are cohort-specific means, not independently measured physical ADE.

| Horizon(s) | Matches/model | Adaptive |      CP | Last-two CV | Window CV |
| ---------- | ------------: | -------: | ------: | ----------: | --------: |
| 0.25       |           958 |   90.584 |  96.192 |      89.831 |    90.584 |
| 0.5        |           935 |  117.972 | 133.027 |     123.285 |   117.972 |
| 1          |           800 |  212.978 | 222.984 |     226.090 |   212.978 |
| 1.5        |           706 |  284.413 | 306.603 |     330.165 |   284.413 |
| 2          |           600 |  368.212 | 375.761 |     414.381 |   368.200 |
| 3          |           459 |  488.908 | 486.246 |     599.654 |   488.908 |

No universal winner or statistical-significance claim. Longer-horizon errors are large;3-second adaptive does not beat CP.

## V. HIGH-MOTION RESULTS

UNVERIFIED as an independently annotated stratum. Camera movement exists in the capture but reviewed turn/high-motion intervals were not supplied. Raw forecasts can move far across the image; unknown future camera motion is explicit. Residual synthetic tests exercise the alternative path without claiming real-turn accuracy.

## W. CROWD RESULTS

UNVERIFIED stratified accuracy. Existing duplicate/fragmented tracks are visible in the debug overlay; robust fits do not repair semantic identity. Lost/freshness-failing entities are unavailable, and new identities receive their own short history. No social trajectory model.

## X. SMALL-OBJECT RESULTS

UNVERIFIED stratified accuracy. Pixel jitter can dominate apparent displacement. The research floor, robust fit and input quality guards reduce some numerical sensitivity but are not small-object qualification. No tiny-object confidence is invented.

## Y. TRACK-FRAGMENTATION RESULTS

Session-local WorldEntityId is the prediction/evaluation key. No old-ID history is borrowed. Gap/single-observation fallback, mismatched session/source/clock and predicted-only exclusion are tested. Real expiry/end-censor counts are reported inT; they cannot be attributed exclusively to identity switches without independent review.

## Z. TRAJECTORY-CORRIDOR RELATION

IMPLEMENTED raw-image point-path intersection with the current frozen convex image polygon. Outside entities remain present; inside→outside, outside→inside, parallel-outside, edge contact and entry/exit between horizons are tested. Bearing/world/stabilized coordinates return UNKNOWN mapping, preserving their independent trajectories. This is a representation limit, not a fabricated metric interaction.

## AA. PREDICTED CORRIDOR ENTRY RESULTS

Analytical square fixture: x=3 moving left at4 units/s enters x=2 after0.25s, including when future sampled endpoint is outside again. Parallel outside has no entry; already-inside entry is0. Name is predicted_corridor_entry_time_ns. Frozen corridor, point extent and unknown user motion make this different from TTC/collision or safety.

## AB. LATENCY P50/P90/P95/P99

Ten-minute-run trajectory P50/P90/P95/P99: 1.154/1.908/2.256/3.240 ms. Final short replay: 2.732/3.729/4.129/5.363 ms. These exclude benchmark counters and upstream inference. The final short replay validates the overflow guard and piecewise corridor helper added during the long run; the long-run timing is not falsely attributed to those last changes.

The isolated compute stress benchmark is separate from upstream cadence. No hard realtime deadline is qualified.

## AC. MANY-ENTITY STRESS

MEASURED200 predictions/count,16 history samples/entity, six horizons. Final implementation P50/P95/P99 in milliseconds:

| Entities |    P50 |    P95 |    P99 |
| -------- | -----: | -----: | -----: |
| 1        |  0.089 |  0.162 |  0.263 |
| 10       |  0.858 |  1.082 |  1.150 |
| 50       |  4.497 |  5.500 |  5.922 |
| 100      |  9.046 | 11.810 | 13.219 |
| 128      | 11.609 | 14.042 | 21.836 |
| 512      | 47.402 | 62.572 | 79.260 |

Large-count latency exceeds the few-ms target. No entity-pair interactions or unbounded trajectory history. Whole-process RSS is exported in JSON; shared-machine timing is not a universal deadline/leak guarantee.

## AD. TEN-MINUTE REPLAY

MEASURED 600.892 seconds wall, at least 600 seconds source span: 446 WorldState/CorridorAnalysis/TrajectorySet updates, 8961 trajectory hypotheses, zero processing failures. Model counts: {'CONSTANT_POSITION': 8961}. Quality: {'DEGRADED': 8927, 'UNRELIABLE': 34}. Whole-process RSS start/peak/end: 127475712/763002880/728461312 bytes, including upstream models/JVM. Final short replay also completed with zero processing failures.

## AE. FULL-PIPELINE UPDATE RATE

0.7433 source updates/s versus Task012's482/600 =0.8033. Difference -7.47%. This is below wearable realtime targets. Sparse updates exceed the default observation-gap gate, so constant-position fallback is expected; offline dense updates exercise velocity fitting. Median/P95 arrival intervals: 1.267/1.767 seconds.

## AF. THROUGHPUT OVERHEAD

Timed trajectory compute totaled 0.545s, 0.0907% of wall time. It is not the dominant bottleneck. Historical rate differences cannot be causally assigned to Task013 without a controlled paired hardware experiment; no speedup claim. The final short replay measures the final helper implementation separately.

The first long run overlapped another model replay/build work and is excluded from clean throughput comparison. Historical Task012482 updates is a reference, not a controlled paired experiment. Predictor compute and upstream arrival intervals are measured separately; slow perception cannot be disguised by fast prediction math.

## AG. PREDICTOR SWAP TEST

PASS: CP, last-two, window/adaptive configurations publish the same immutable contract. Pipeline supports an injected TrajectoryPredictor; no downstream implementation-specific import is needed. Tests cover config requirements, schema8 recording, deterministic output and immutability.

## AH. COMPONENT REPLACEMENT AUDIT

PASS for normalized boundaries: detector/tracker/depth/flow/ego/segmenter remain upstream of WorldState. Alternative world provenance/entity-count fixtures, synthetic depth/pose producers and alternate corridor polygons operate through contracts. Unsupported representations remain explicitly unavailable; a component swap does not validate its evidence.

## AI. TASK001–013 INTEGRATION AUDIT

See docs/architecture/TASK001_013_INTEGRATION_AUDIT.md. Sequential software interfaces001→002 through012→013 are preserved/PASS. Additional004→013 and011→013 PASS.007→013 identity continuity,008→013 metric truth,009→013 compensated future-view reference and012→013 non-image interaction mapping are PARTIAL research/representation limits. They are not silently called production-qualified.

## AJ. FUTURE TASK014 CONTRACT

WorldState + CorridorAnalysis + TrajectorySet, matching session/source-state timestamp. Consumers must inspect domain, units, frame, status, quality, envelope and provenance before meaningful relative-approach/intersection/TTC/CPA evidence. Image entry time is not physical TTC. Task014 is not implemented.

## AK. FUTURE TASK015 CONTRACT

Future risk policy consumes evidence validity/quality, corridor relation, uncertainty and later qualified interaction metrics, without importing predictor classes. No risk thresholds, alert, hazard, navigation or user-speed assumption added.

## AL. R&D EXPERIMENTS

Twenty RND-TRAJ entries exist with question, motivation, hypothesis, experiment, metrics, criterion and status. Synthetic/engineering experiments are distinguished from planned independent crowd/small-object/body-motion/physical qualification. CA and learned trajectories remain deferred.

## AM. PRIVACY / SECURITY

No new network service, cloud upload, identity recognition, biometrics or cross-session identity. Footage and eight opt-in overlays remain local/Git-ignored. Public results omit private paths/images. Production Next.js16.4.0 was affected by two critical and one high advisory; updated to16.4.2 per the [maintainer bulletin](https://nextjs.org/blog/nextjs-security-update-october-14-2026). npm security gate now reports no unreviewed advisories; five previously reviewed development-only braces-chain entries remain, with no compatible patch identified by npm. No audit bypass/forced downgrade.

## AN. ADVERSARIAL AUDIT

CRITICAL fixed: affected production Next.js dependency; patched dependency/lockfile and rebuilt. No outstanding Task013 critical implementation defect identified.

HIGH fixed: calibration identity missing from historical bearing/world candidates; source history now retains identity and predictor gates it. Future/regressing/mixed-clock inputs and prediction feedback are rejected/excluded. Initial evaluation queue overflow invalidated unequal cohorts; revised bounded sampling produced zero overflow and equal model cohorts. Initial costly all-pairs seed replaced with separated-pair median/OLS. No outstanding Task013 high implementation defect identified. The inherited high-severity development dependency advisory remains explicitly accepted under the existing narrow gate, not fixed.

MEDIUM: inaccurate long-horizon raw-image forecasts, upstream cadence, identity corruption, non-independent tracker references, unavailable real compensated/world truth and unreviewed scenario strata. Recommended fix: independently reviewed stratified footage/calibration/pose measurements and controlled hardware qualification before physical claims.

LOW: dense debug-overlay clutter and richer coordinate/envelope adapters. Recommended fix: optional viewer filtering and explicit future adapters without changing evidence semantics. No object annotations were rewritten or marked human-reviewed.

Final robustness fixes in trajectory_fit.py reject non-finite fitted results from extreme finite inputs; trajectory_corridor.py tests each successive prediction segment rather than assuming every replacement predictor follows the origin-to-final chord. Three additional regression cases cover these paths. The final short replay and full verification include both fixes; the ten-minute replay predates them as stated in sectionAB.

## AO. TEST COUNTS

665 total:192 Guardian +446 perception-lab +24 web +3 API. Task013 adds49 Python tests, including causal retrospective scoring, exact metric history, calibration rejection, outlier handling, unit separation, predictor configs, many-entity cases, corridor entry, recording and overlay immutability. Tests are software checks, not human or physical validation.

## AP. FULL VERIFICATION

PASS: npm run verify completed exit0, evidence benchmark-results/task013-final-verify-v3.log. Includes Prettier, Ruff, strict mypy68 source files, ESLint, strict TypeScript, Spotless, SpotBugs,665 tests, production builds, security review and smoke (API contracts, home page,8 concurrent health requests, API outage). The first full attempt failed the Next.js advisory gate and is preserved, not claimed as passed. System-temp pytest runs avoid the reproduced OneDrive recorder-finalization failure. No hosted CI/cloud/mobile/hardware qualification was executed.

## AQ. PRIMARY_TRAJECTORY_PREDICTOR_FOR_TASK014

PROVISIONAL: AdaptiveKinematicPredictor with bounded robust window fitting, exact source gates and explicit domain validity. Selection reflects synthetic noise robustness, modest real short-horizon proxy improvement and bounded compute, not validated physical forecasting.

## AR. FALLBACK_TRAJECTORY_PREDICTOR

CONSTANT_POSITION for insufficient/stationary/unstable history. Unavailable when source identity/freshness is invalid. No invented velocity to keep a pipeline green.

## AS. REMAINING RISKS

Physical motion/depth/pose and production safety remain unvalidated. Real source is the existing development capture with tracker-reference bias, not independent qualification data. All semantic human review remains deferred/unverified. Large-count latency and upstream cadence are not wearable realtime qualified. Metric corridor interaction mapping is unavailable, long-horizon errors are large, and five reviewed development advisory entries remain. No future-error-free guarantee or production deployment claim.

## AT. FINAL VERDICT

TASK013 COMPLETE: YES — local prototype/research scope.

ENGINEERING QUALIFIED FOR TASK014: YES — with explicit research validity gates and the remaining limitations above.

PHYSICAL_TRAJECTORY_VALIDATED: NO.

COLLISION_PREDICTION_VALIDATED: NO.

PRODUCTION_SAFETY_VALIDATED: NO.

Task014 not started.
