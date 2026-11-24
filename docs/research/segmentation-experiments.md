# Task010 research experiments

No fabricated ground truth, training or safety claim. Runtime measurements are in the Task010 report; pending experiments are explicit.

## RND-SEG-001

QUESTION: PIDNet-S quality/latency.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: A small PIDNet can provide useful surfaces within a CPU budget.

EXPERIMENT: Run frozen first-person frames; compare reviewed masks and elapsed times.

METRICS: per-class recall, false traversable evidence, latency.

DECISION CRITERION: Accept only after reviewed coverage/error analysis.

STATUS: MEASURED runtime; quality awaits review.

## RND-SEG-002

QUESTION: PP-LiteSeg quality/latency.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: A lightweight alternate can reduce CPU cost.

EXPERIMENT: Same frozen frames and taxonomy.

METRICS: IoU, boundary F1, latency.

DECISION CRITERION: Compare accuracy/cost without treating disagreement as truth.

STATUS: MEASURED runtime; quality awaits review.

## RND-SEG-003

QUESTION: Research reference.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: An extra reference may expose systematic gaps.

EXPERIMENT: Only add if two baselines fail and rights permit.

METRICS: quality gain, setup cost, rights.

DECISION CRITERION: Require meaningful gain before adding dependencies.

STATUS: DEFERRED OPTIONAL.

## RND-SEG-004

QUESTION: Input resolution.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: Higher resolution may improve narrow boundaries at extra cost.

EXPERIMENT: PIDNet 512x256 versus 768x384.

METRICS: boundary F1, recall, latency, RSS.

DECISION CRITERION: Require reviewed boundary gain worth measured cost.

STATUS: IMPLEMENTED comparison; quality awaits review.

## RND-SEG-005

QUESTION: Sidewalk/road/path recall.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: Pretrained taxonomy may miss pedestrian-specific surfaces.

EXPERIMENT: Stratify reviewed labels and unsupported classes.

METRICS: per-class recall and support.

DECISION CRITERION: Unsupported PATH/FLOOR cannot be described as absent.

STATUS: HUMAN REVIEW REQUIRED.

## RND-SEG-006

QUESTION: False traversable evidence.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: Appearance can misclassify obstacles as ground.

EXPERIMENT: Evaluate reviewed non-ground pixels against potential evidence.

METRICS: false proposal fraction, obstacle-as-ground pixels.

DECISION CRITERION: Report counts and denominators per split; never safety probability.

STATUS: Metric tested; real labels pending.

## RND-SEG-007

QUESTION: Boundary accuracy.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: Small boundary errors can matter more than region average.

EXPERIMENT: Ignore-aware boundary comparison.

METRICS: one-pixel precision/recall/F1.

DECISION CRITERION: Missed boundary must score zero rather than vanish.

STATUS: Metric analytically tested; review pending.

## RND-SEG-008

QUESTION: Crowd occlusion.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: Crowds remove visible ground.

EXPERIMENT: Review crowd scenario frames.

METRICS: visible-ground coverage, false evidence.

DECISION CRITERION: No hallucinated observed ground beneath people.

STATUS: SCENARIO REVIEW REQUIRED.

## RND-SEG-009

QUESTION: Low light.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: Dark scenes may degrade surface classification.

EXPERIMENT: Review genuine low-light scenes, not brightness proxies alone.

METRICS: class confusion, unknown fraction.

DECISION CRITERION: Report insufficient data if no supported cases.

STATUS: SCENARIO REVIEW REQUIRED.

## RND-SEG-010

QUESTION: High motion.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: Blur and camera turns may degrade masks.

EXPERIMENT: Review turning frames and compare fresh predictions.

METRICS: recall, boundary error, result age.

DECISION CRITERION: No temporal agreement claim from unaligned pixels.

STATUS: SCENARIO REVIEW REQUIRED.

## RND-SEG-011

QUESTION: Shadow robustness.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: Shadows may split continuous surfaces.

EXPERIMENT: Tag shadowed surfaces and inspect errors.

METRICS: class confusion, fragmentation.

DECISION CRITERION: Need independently reviewed labels.

STATUS: SCENARIO REVIEW REQUIRED.

## RND-SEG-012

QUESTION: Morphology.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: Cleanup can erase narrow paths or fill unknown holes.

EXPERIMENT: Controlled future opening/closing ablation.

METRICS: boundary error, unknown preservation.

DECISION CRITERION: Reject methods that fill unknown as traversable.

STATUS: DEFERRED; no morphology by default.

## RND-SEG-013

QUESTION: Bottom connectivity.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: Bottom contact may be useful context, not safety.

EXPERIMENT: Disconnected-island synthetic fixture; real review later.

METRICS: component area, bottom flag.

DECISION CRITERION: Preserve both connected and disconnected semantic regions.

STATUS: ANALYTICAL PASS.

## RND-SEG-014

QUESTION: Detection integration.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: Object evidence should not destroy surface semantics.

EXPERIMENT: Swap generic detector provenance and known boxes.

METRICS: occupancy area, oversized-box diagnostics.

DECISION CRITERION: Original mask unchanged; exact identities required.

STATUS: ANALYTICAL PASS; PicoDet-S and YOLOX-Nano coexistence each passed 90 frames with 3 semantic updates and zero failures.

## RND-SEG-015

QUESTION: Depth consistency.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: Depth jumps may flag geometry change without validated meters.

EXPERIMENT: Synthetic discontinuity and alternate provider provenance.

METRICS: relative jump percentile, valid neighbor count.

DECISION CRITERION: No step-height or safe-slope claim.

STATUS: ANALYTICAL PASS.

## RND-SEG-016

QUESTION: Flow propagation.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: Warping could help lower semantic cadence.

EXPERIMENT: Future exact-pair flow warp with disocclusion handling.

METRICS: agreement, boundary error, unknown growth.

DECISION CRITERION: Always PROPAGATED with age; no hidden inpainting.

STATUS: DELIBERATELY DEFERRED.

## RND-SEG-017

QUESTION: Semantic cadence.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: One-job scheduling avoids inference backlog.

EXPERIMENT: Busy-worker test and source-PTS replay.

METRICS: skips, updates, age, queue depth.

DECISION CRITERION: Bound job count; measure achieved throughput.

STATUS: Worker test PASS; replay measurement in report.

## RND-SEG-018

QUESTION: Propagation age.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: Older predicted masks become unreliable.

EXPERIMENT: Future age-stratified reviewed-mask experiment.

METRICS: error versus age and warp count.

DECISION CRITERION: Expire masks rather than silently refresh timestamps.

STATUS: DEFERRED with propagation.

## RND-SEG-019

QUESTION: Model disagreement.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: Differences can prioritize annotation.

EXPERIMENT: Compare predictions on identical hashed frames.

METRICS: pixel agreement per frame.

DECISION CRITERION: Use for review ordering, never ground truth.

STATUS: MEASURED DIAGNOSTIC.

## RND-SEG-020

QUESTION: Pretrained sufficiency.

WHY IT MATTERS: Surface evidence must remain useful, bounded and honest about uncertainty.

HYPOTHESIS: Urban scene weights may be insufficient for pedestrian surfaces.

EXPERIMENT: Review all three splits and taxonomy gaps before deciding.

METRICS: coverage, false evidence, rights, runtime.

DECISION CRITERION: No automatic selection from runtime alone; no training on test.

STATUS: UNVALIDATED pending human review.
