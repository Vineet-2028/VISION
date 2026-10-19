# Task009 motion research questions

Prototype hypotheses; no physical-motion or safety qualification.

## RND-FLOW-001

QUESTION: Sparse LK versus DIS.

WHY: Choose bounded CPU baseline.

HYPOTHESIS: LK is cheaper at adequate sparse coverage.

EXPERIMENT: Hashed prototype pairs with both providers.

METRICS: latency, valid fraction, coverage.

DECISION CRITERION: Prefer lower cost without unacceptable coverage loss.

STATUS: MEASURED; LK provisionally selected.

## RND-FLOW-002

QUESTION: Forward/backward filtering benefit.

WHY: Reject unstable correspondences.

HYPOTHESIS: FB reduces bad matches.

EXPERIMENT: Known translation and reversal plus real diagnostics.

METRICS: FB error, validity, displacement error.

DECISION CRITERION: Known translation recovered; future labeled-flow ablation needed.

STATUS: IMPLEMENTED/ANALYTICALLY TESTED; real benefit unvalidated.

## RND-FLOW-003

QUESTION: Learned flow benefit/cost.

WHY: Avoid unnecessary dependencies.

HYPOTHESIS: Classical methods suffice for foundation.

EXPERIMENT: Optional isolated learned reference later.

METRICS: accuracy, memory, latency, rights.

DECISION CRITERION: Integrate only with measured benefit and clear rights.

STATUS: DEFERRED OPTIONAL.

## RND-EGO-001

QUESTION: Essential rotation accuracy/stability.

WHY: Separate camera motion.

HYPOTHESIS: Calibrated robust matches recover synthetic pose.

EXPERIMENT: Known varying-depth 3D points.

METRICS: rotation/direction error, failure states.

DECISION CRITERION: Analytical error within test tolerance.

STATUS: ANALYTICAL PASS; real pose unvalidated.

## RND-EGO-002

QUESTION: Visual versus IMU disagreement.

WHY: Detect inconsistent evidence.

HYPOTHESIS: Matched rotations agree in synthetic setup.

EXPERIMENT: Nonidentity mount and timestamp-matched poses.

METRICS: angular disagreement.

DECISION CRITERION: Reject pair mismatch; zero self-disagreement.

STATUS: ANALYTICAL PASS; real IMU N/A.

## RND-EGO-003

QUESTION: Dynamic masking benefit.

WHY: Reduce moving-feature contamination.

HYPOTHESIS: Masking changes support conservatively.

EXPERIMENT: Real pairs with/without prototype boxes.

METRICS: coverage, inliers, failure rate.

DECISION CRITERION: No claim without static/dynamic labels.

STATUS: MEASURED DIAGNOSTIC.

## RND-EGO-004

QUESTION: Essential versus homography degeneracy.

WHY: Avoid fabricated translation.

HYPOTHESIS: High homography support detects planar ambiguity.

EXPERIMENT: Synthetic/real calibrated pairs.

METRICS: support ratio, unavailable reason.

DECISION CRITERION: Planar support suppresses translation.

STATUS: IMPLEMENTED; broader validation open.

## RND-EGO-005

QUESTION: Depth PnP feasibility.

WHY: Prepare research scaled motion.

HYPOTHESIS: Exact metric synthetic depth supports PnP.

EXPERIMENT: Known 3D points and image correspondences.

METRICS: transform/reprojection error.

DECISION CRITERION: Recover known transform; reject stale/relative depth.

STATUS: ANALYTICAL PASS.

## RND-EGO-006

QUESTION: Metric-depth scale sensitivity.

WHY: Do not promote model scale.

HYPOTHESIS: Scaled depth scales research translation.

EXPERIMENT: Future measured-depth intervention.

METRICS: translation scale error.

DECISION CRITERION: No metric qualification without reference distances.

STATUS: UNVALIDATED.

## RND-MOTION-001

QUESTION: Rotation compensation residual reduction.

WHY: Remove apparent rotational movement.

HYPOTHESIS: Static synthetic rays yield zero residual.

EXPERIMENT: Known camera rotation.

METRICS: residual magnitude.

DECISION CRITERION: Near-zero analytical residual.

STATUS: ANALYTICAL PASS; real static labels unavailable.

## RND-MOTION-002

QUESTION: Translation compensation benefit.

WHY: Account for parallax.

HYPOTHESIS: Known depth and translation reduce residual.

EXPERIMENT: Synthetic PnP and compensation.

METRICS: residual magnitude.

DECISION CRITERION: Near-zero synthetic residual.

STATUS: ANALYTICAL PASS; real unvalidated.

## RND-MOTION-003

QUESTION: Dynamic/background separability.

WHY: Prepare future motion reasoning.

HYPOTHESIS: Independent pixels retain residual.

EXPERIMENT: Injected moving subset with same camera rotation.

METRICS: subset/background residual.

DECISION CRITERION: Moving subset nonzero and background near zero.

STATUS: ANALYTICAL PASS; real labels unavailable.

## RND-MOTION-004

QUESTION: Flow-assisted tracking benefit.

WHY: Improve Task007 without coupling.

HYPOTHESIS: Flow may help association.

EXPERIMENT: Optional later controlled tracking comparison.

METRICS: identity switches, IDF1, cost.

DECISION CRITERION: Adopt only after measurable benefit.

STATUS: DEFERRED OPTIONAL; tracker unchanged.

## RND-FLOW-004

QUESTION: Low-light degradation.

WHY: Assess weak texture.

HYPOTHESIS: Poor light lowers reliable features.

EXPERIMENT: Future independently tagged low-light clips.

METRICS: features, validity, failures.

DECISION CRITERION: Report failures without selection bias.

STATUS: UNVALIDATED; no night qualification.

## RND-FLOW-005

QUESTION: High rotation degradation.

WHY: Assess head turns.

HYPOTHESIS: Large displacement challenges pyramids.

EXPERIMENT: Analytical rotations; future tagged turns.

METRICS: error, support, latency.

DECISION CRITERION: Fail closed outside supported gaps/coverage.

STATUS: ANALYTICAL ONLY.

## RND-FLOW-006

QUESTION: Crowd behavior.

WHY: Static-majority assumption can fail.

HYPOTHESIS: Masking may leave insufficient support.

EXPERIMENT: Dynamic exclusions and future labeled crowd.

METRICS: coverage, unavailable rate.

DECISION CRITERION: Explicit degradation, no safety probability.

STATUS: ANALYTICAL/CONTRACT TESTS; real unvalidated.

## RND-PERF-001

QUESTION: Flow cadence versus CPU cost.

WHY: Choose workable research cadence.

HYPOTHESIS: LK costs less than dense DIS.

EXPERIMENT: Two providers and requested 10Hz replay.

METRICS: P50/P90/P95/P99/max, published rate.

DECISION CRITERION: Report achieved rate rather than request.

STATUS: MEASURED.

## RND-PERF-002

QUESTION: Long-run stability.

WHY: Bound buffers and work.

HYPOTHESIS: One previous frame and bounded arrays remain stable.

EXPERIMENT: Ten-minute footage plus 2000 allocation-release cycles.

METRICS: RSS, queue, drops, failures.

DECISION CRITERION: Finite queue and no retained old dense arrays.

STATUS: MEASUREMENT IN REPORT.
