# World-model research experiments

Engineering evidence only; no fabricated semantic truth or safety measurements.

## RND-WM-001

QUESTION: Source freshness policy.

WHY IT MATTERS: Different model rates require explicit ages.

HYPOTHESIS: Separate freshness from validity.

EXPERIMENT: Async timeline and real source-age distributions.

METRICS: age/status, rejection count.

DECISION CRITERION: No old observation relabeled current.

STATUS: IMPLEMENTED; timeline tests passed; replay measurements in report.

## RND-WM-002

QUESTION: Track-to-world identity mapping.

WHY IT MATTERS: Tracker IDs are replaceable.

HYPOTHESIS: Explicit mapping allows conservative splits.

EXPERIMENT: Change TrackId at identical geometry.

METRICS: IDs, retained histories.

DECISION CRITERION: New ID with no inherited unrelated history.

STATUS: TESTED.

## RND-WM-003

QUESTION: Depth staleness.

WHY IT MATTERS: Predictions must not refresh depth.

HYPOTHESIS: Carry old values only with old identity and stale status.

EXPERIMENT: Observed-depth then predicted-track timeline.

METRICS: depth age/status.

DECISION CRITERION: Old depth remains stale, not a new sample.

STATUS: TESTED.

## RND-WM-004

QUESTION: Semantic staleness.

WHY IT MATTERS: Sparse inference has long gaps.

HYPOTHESIS: Freshness and propagated status are separate axes.

EXPERIMENT: Propagated/stale surface timeline.

METRICS: source age, status.

DECISION CRITERION: Propagation never becomes observation.

STATUS: TESTED.

## RND-WM-005

QUESTION: Unverified semantics.

WHY IT MATTERS: Model proposals are not ground truth.

HYPOTHESIS: Validation remains UNVERIFIED through all derivations.

EXPERIMENT: Center disagreement and surface tests.

METRICS: validation flags, category.

DECISION CRITERION: No category override or trusted fact.

STATUS: TESTED.

## RND-WM-006

QUESTION: Camera versus world positions.

WHY IT MATTERS: Pose is often missing.

HYPOTHESIS: Only exact pose permits world estimates.

EXPERIMENT: Analytical depth/pose fixture and stale pose.

METRICS: point coordinates/availability.

DECISION CRITERION: Camera (0,0,5), world (1,2,5); no relative metric point.

STATUS: TESTED.

## RND-WM-007

QUESTION: Entity expiry.

WHY IT MATTERS: Long sessions must not accumulate objects.

HYPOTHESIS: Bounded expiry removes old mappings.

EXPERIMENT: Observed/predicted/lost/expired timeline.

METRICS: entity count, ID reuse.

DECISION CRITERION: Removal without ID reuse.

STATUS: TESTED.

## RND-WM-008

QUESTION: Late events.

WHY IT MATTERS: Sources complete out of order.

HYPOTHESIS: Per-source watermark and late window are deterministic.

EXPERIMENT: t0,t2,t1 plus future and duplicate events.

METRICS: history count, diagnostics.

DECISION CRITERION: No rewind or double evidence.

STATUS: TESTED.

## RND-WM-009

QUESTION: Quality aggregation.

WHY IT MATTERS: Unrelated confidences are incomparable.

HYPOTHESIS: Capability-specific reasons are more honest than averaging.

EXPERIMENT: Zero/partial pipeline fixtures.

METRICS: capability status, reasons.

DECISION CRITERION: Image tracks survive absent metric evidence.

STATUS: TESTED; calibration of quality remains UNVALIDATED.

## RND-WM-010

QUESTION: Component failures.

WHY IT MATTERS: Failure is not empty scene.

HYPOTHESIS: Retain supported entities while exposing failures.

EXPERIMENT: Depth/segmentation injection and failure metadata tests.

METRICS: entity status, failure reason, source age.

DECISION CRITERION: No crash, no retimestamping.

STATUS: TESTED.

## RND-WM-011

QUESTION: Partial-pipeline usefulness.

WHY IT MATTERS: Optional models may be absent.

HYPOTHESIS: Image-space state remains useful.

EXPERIMENT: No depth/semantics/flow replay and fixture.

METRICS: snapshots, unavailable fields.

DECISION CRITERION: Coherent partial state.

STATUS: TESTED; real partial replay measured.

## RND-WM-012

QUESTION: Snapshot cadence.

WHY IT MATTERS: Model rates differ from publication rate.

HYPOTHESIS: Frame-driven publication can decouple models.

EXPERIMENT: 90-frame offline and real-time replay.

METRICS: world updates/model outputs.

DECISION CRITERION: Independent world publication without waiting for every source.

STATUS: MEASURED in results.

## RND-WM-013

QUESTION: World-model latency.

WHY IT MATTERS: Fusion should not dominate inference.

HYPOTHESIS: Compact state keeps update costs small.

EXPERIMENT: Timed ingest/snapshot on real and synthetic workloads.

METRICS: P50/P90/P95/P99.

DECISION CRITERION: Fusion materially below observed model cost; no production threshold.

STATUS: MEASURED in results.

## RND-WM-014

QUESTION: Long-run memory.

WHY IT MATTERS: Session length must not grow retained state.

HYPOTHESIS: Hard caps and expiry bound internal storage.

EXPERIMENT: 10-minute replay and 2000-step synthetic loads.

METRICS: RSS, entity/history/region peaks.

DECISION CRITERION: Respect caps; no retained dense payload history.

STATUS: MEASURED in results; no universal leak proof.

## RND-WM-015

QUESTION: Many-entity scaling.

WHY IT MATTERS: Crowds stress snapshot cost.

HYPOTHESIS: Cost scales with bounded current entities.

EXPERIMENT: 1/10/50/100/129 inputs, 2000 updates each.

METRICS: update/snapshot percentiles, cap.

DECISION CRITERION: 129 inputs retain at most128.

STATUS: MEASURED in results.

## RND-WM-016

QUESTION: Component swaps.

WHY IT MATTERS: Provider choice must remain local.

HYPOTHESIS: Sentinel contracts avoid downstream vendor branches.

EXPERIMENT: PicoDet/YOLOX replays, tracker/depth/flow/ego/semantic provenance fixtures.

METRICS: same output schema.

DECISION CRITERION: No WorldModel code change.

STATUS: TESTED/MEASURED.

## RND-WM-017

QUESTION: Track-ID switches.

WHY IT MATTERS: Identity continuity is imperfect.

HYPOTHESIS: False splits are preferable to silent merges.

EXPERIMENT: Same box with changed ID.

METRICS: entity/history mapping.

DECISION CRITERION: Separate identities.

STATUS: TESTED; real continuity remains UNVALIDATED.

## RND-WM-018

QUESTION: Depth/pose disagreement.

WHY IT MATTERS: Mismatched transforms produce false positions.

HYPOTHESIS: Exact joins reject current-pose substitution.

EXPERIMENT: Fresh depth with different pose identity.

METRICS: world point, reason.

DECISION CRITERION: World point unavailable with explicit reason.

STATUS: TESTED.

## RND-WM-019

QUESTION: Mobile representation.

WHY IT MATTERS: Future portability needs bounded plain values.

HYPOTHESIS: Frozen records can map to Java/Kotlin.

EXPERIMENT: Inspect schema fields and serialization test.

METRICS: dense/vendor objects, bounded counts.

DECISION CRITERION: No model tensors or Python-only identity semantics.

STATUS: STATIC AUDIT; mobile runtime PLANNED.

## RND-WM-020

QUESTION: Probabilistic fusion.

WHY IT MATTERS: Premature probabilities imply calibration.

HYPOTHESIS: Explicit evidence suffices for prototype.

EXPERIMENT: Review current evidence/uncertainty availability.

METRICS: calibrated likelihood availability.

DECISION CRITERION: No probabilistic fusion until justified.

STATUS: DEFERRED; no calibrated measurement model.
