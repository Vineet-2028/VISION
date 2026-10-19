# Depth research experiments

No entry implies production metric accuracy. Measurements use local RGB footage without metric ground truth.

## RND-DEP-001 — Depth Anything Small relative

- QUESTION: Depth Anything Small relative.
- WHY IT MATTERS: Ordering without a metric claim.
- HYPOTHESIS: Small can provide usable ordering offline.
- EXPERIMENT: Two-size local replay.
- METRICS: latency, validity, region spread.
- DECISION CRITERION: Explicit units, finite output and measured cost.
- STATUS: MEASURED; no ordinal ground truth.

## RND-DEP-002 — Depth Anything outdoor metric

- QUESTION: Depth Anything outdoor metric.
- WHY IT MATTERS: Metric research needs a real provider.
- HYPOTHESIS: Outdoor checkpoint produces finite Z.
- EXPERIMENT: Two-size local replay.
- METRICS: validity, supported range, latency.
- DECISION CRITERION: Finite explicit model-estimated Z; accuracy remains separate.
- STATUS: MEASURED; metric accuracy UNVALIDATED.

## RND-DEP-003 — Metric3D comparison

- QUESTION: Metric3D comparison.
- WHY IT MATTERS: Intrinsics influence scale.
- HYPOTHESIS: May improve metric generalization.
- EXPERIMENT: Review intrinsics, runtime and artifact terms.
- METRICS: requirements, rights, resource cost.
- DECISION CRITERION: No invented intrinsics or assumed weight license.
- STATUS: INVESTIGATED; integration deferred.

## RND-DEP-004 — FastDepth baseline

- QUESTION: FastDepth baseline.
- WHY IT MATTERS: Lightweight alternatives may reduce latency.
- HYPOTHESIS: Small indoor model may be cheap.
- EXPERIMENT: Review official runtime/domain.
- METRICS: integration cost, domain, rights.
- DECISION CRITERION: Clean integration and applicable domain before acquisition.
- STATUS: INVESTIGATED; not benchmarked.

## RND-DEP-005 — Relative versus metric

- QUESTION: Relative versus metric.
- WHY IT MATTERS: Prevent unit confusion.
- HYPOTHESIS: Same downstream contracts can preserve distinctions.
- EXPERIMENT: Swap real and synthetic providers.
- METRICS: unit/direction assertions.
- DECISION CRITERION: Relative never exposes meters.
- STATUS: IMPLEMENTED and tested; real comparison measured.

## RND-DEP-006 — Region sampling

- QUESTION: Region sampling.
- WHY IT MATTERS: Background can dominate boxes.
- HYPOTHESIS: Robust ROI strategies differ.
- EXPERIMENT: Five strategies on bounded real boxes.
- METRICS: valid fraction, median, MAD.
- DECISION CRITERION: Document variation; no accuracy winner without truth.
- STATUS: MEASURED.

## RND-DEP-007 — Box erosion

- QUESTION: Box erosion.
- WHY IT MATTERS: Edges may include background.
- HYPOTHESIS: Inset reduces some contamination.
- EXPERIMENT: Central/eroded/lower comparisons.
- METRICS: region statistics.
- DECISION CRITERION: Compare paired samples; lower spread is not correctness.
- STATUS: PARTIAL; parameter sweep pending.

## RND-DEP-008 — Bottom versus median

- QUESTION: Bottom versus median.
- WHY IT MATTERS: Grounded-object geometry may differ.
- HYPOTHESIS: Bottom patches disagree with visible-surface median.
- EXPERIMENT: Compare bottom patch and eroded median.
- METRICS: paired relative difference.
- DECISION CRITERION: Retain both diagnostics, do not fuse.
- STATUS: MEASURED.

## RND-DEP-009 — Temporal stability

- QUESTION: Temporal stability.
- WHY IT MATTERS: Flicker affects future consumers.
- HYPOTHESIS: Per-frame outputs vary with motion.
- EXPERIMENT: Adjacent-frame same-region diagnostic.
- METRICS: median change, missing samples.
- DECISION CRITERION: Report variability, not distance error.
- STATUS: MEASURED on six adjacent frames; motion and prototype identities confound interpretation.

## RND-DEP-010 — Low light

- QUESTION: Low light.
- WHY IT MATTERS: Dark inputs may degrade depth.
- HYPOTHESIS: Validity can remain high despite wrong predictions.
- EXPERIMENT: Reviewed low-light subset.
- METRICS: validity, spread, latency.
- DECISION CRITERION: Scenario verified before claim.
- STATUS: UNVALIDATED; scenario labels UNKNOWN.

## RND-DEP-011 — High motion

- QUESTION: High motion.
- WHY IT MATTERS: Camera motion affects temporal interpretation.
- HYPOTHESIS: Motion increases variation.
- EXPERIMENT: Reviewed turning/walking subset.
- METRICS: changes, missing rate.
- DECISION CRITERION: No physical-velocity inference.
- STATUS: UNVALIDATED.

## RND-DEP-012 — Crowd contamination

- QUESTION: Crowd contamination.
- WHY IT MATTERS: Overlapping people mix surfaces.
- HYPOTHESIS: Generic boxes include background/other people.
- EXPERIMENT: Reviewed occlusion subset.
- METRICS: strategy disagreement.
- DECISION CRITERION: Report individual failures.
- STATUS: UNVALIDATED.

## RND-DEP-013 — Tiny and thin objects

- QUESTION: Tiny and thin objects.
- WHY IT MATTERS: Depth resolution loses narrow structures.
- HYPOTHESIS: Sampling misses poles/spokes.
- EXPERIMENT: Verified thin-object regions.
- METRICS: native pixel support, disagreement.
- DECISION CRITERION: No generic success claim.
- STATUS: UNVALIDATED.

## RND-DEP-014 — Depth cadence

- QUESTION: Depth cadence.
- WHY IT MATTERS: Expensive models need slower scheduling.
- HYPOTHESIS: Independent cadence preserves bounded state.
- EXPERIMENT: 2 Hz long and 5 Hz short replay.
- METRICS: achieved rate, age, memory, availability.
- DECISION CRITERION: Measure deficits and keep stale unavailable.
- STATUS: MEASURED; requested rates not achieved; corrected long and alternate-detector replays complete.

## RND-DEP-015 — Native versus ONNX

- QUESTION: Native versus ONNX.
- WHY IT MATTERS: Export may change semantics.
- HYPOTHESIS: Export could preserve maps approximately.
- EXPERIMENT: Pinned export parity on real frames.
- METRICS: mask agreement, relative error, samples.
- DECISION CRITERION: Predeclare tolerance; no bit equality requirement.
- STATUS: LIMITED PASS for one fixed-shape relative-model export; broader and metric parity unvalidated.

## RND-DEP-016 — Ground consistency

- QUESTION: Ground consistency.
- WHY IT MATTERS: Geometry gives independent candidate.
- HYPOTHESIS: Calibrated grounded objects may agree.
- EXPERIMENT: Use measured calibration and ground pose.
- METRICS: difference, missing intersections.
- DECISION CRITERION: No fusion or perfect-ground-truth assumption.
- STATUS: UNAVAILABLE for current real footage.

## RND-DEP-017 — Track ID robustness

- QUESTION: Track ID robustness.
- WHY IT MATTERS: Identity switches are known.
- HYPOTHESIS: Per-frame depth survives ID replacement.
- EXPERIMENT: Alternate public TrackSet fixture.
- METRICS: identity and sample equality.
- DECISION CRITERION: No silent history transfer.
- STATUS: TESTED.

## RND-DEP-018 — Stale policy

- QUESTION: Stale policy.
- WHY IT MATTERS: Old depth must not appear fresh.
- HYPOTHESIS: Unavailable policy is unambiguous.
- EXPERIMENT: Asynchronous and predicted fixtures.
- METRICS: status/frame/age.
- DECISION CRITERION: No wrong-frame or predicted fresh sample.
- STATUS: TESTED.

## RND-DEP-019 — Temporal fusion need

- QUESTION: Temporal fusion need.
- WHY IT MATTERS: Smoothing can hide real motion.
- HYPOTHESIS: Raw output is preferable until characterized.
- EXPERIMENT: Compare raw and robust candidates later.
- METRICS: lag, outliers, real changes.
- DECISION CRITERION: Preserve raw samples; avoid blind smoothing.
- STATUS: DEFERRED deliberately.

## RND-DEP-020 — Mobile feasibility

- QUESTION: Mobile feasibility.
- WHY IT MATTERS: Desktop cost does not predict devices.
- HYPOTHESIS: Smaller input or acceleration may help.
- EXPERIMENT: Target-device benchmark later.
- METRICS: latency, power, thermal, memory.
- DECISION CRITERION: Measured target budget required.
- STATUS: UNVALIDATED.
