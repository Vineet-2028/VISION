# Risk research register

## RND-RISK-001: rule versus weighted

QUESTION: How should rule versus weighted behave?

WHY IT MATTERS: Avoid unjustified weights.

HYPOTHESIS: Simple rules suffice without independent labels.

EXPERIMENT: Review transparent rule ordering; reject weighted V1.

METRICS: Rule violations, complexity.

DECISION CRITERION: No benefit justified without held-out labels.

STATUS: IMPLEMENTED: weighted rejected.

## RND-RISK-002: occupancy

QUESTION: How should occupancy behave?

WHY IT MATTERS: Static obstacles matter.

HYPOTHESIS: Fresh occupancy retains relevance.

EXPERIMENT: Static inside with no future/TTC.

METRICS: Level, reasons.

DECISION CRITERION: HIGH independent of TTC.

STATUS: TESTED.

## RND-RISK-003: predicted entry

QUESTION: How should predicted entry behave?

WHY IT MATTERS: Crossings differ from parallel.

HYPOTHESIS: Earlier usable entry ranks higher.

EXPERIMENT: 0.5/1/2-second thresholds.

METRICS: Level distribution.

DECISION CRITERION: Document sensitivity without tuning.

STATUS: MEASURED in report.

## RND-RISK-004: minimum separation

QUESTION: How should minimum separation behave?

WHY IT MATTERS: Units differ.

HYPOTHESIS: Raw distance weights would mislead.

EXPERIMENT: Review pixel versus research-meter eligibility.

METRICS: Unit violations.

DECISION CRITERION: No cross-unit weight.

STATUS: IMPLEMENTED: diagnostic only.

## RND-RISK-005: approach/recession

QUESTION: How should approach/recession behave?

WHY IT MATTERS: Approach is not collision.

HYPOTHESIS: Receding inside stays relevant.

EXPERIMENT: Inside receding fixture.

METRICS: Ordering.

DECISION CRITERION: ELEVATED, not automatic LOW.

STATUS: TESTED.

## RND-RISK-006: static obstacle

QUESTION: How should static obstacle behave?

WHY IT MATTERS: Zero velocity is not absence.

HYPOTHESIS: Occupancy survives no TTC.

EXPERIMENT: Stationary fixture.

METRICS: Level.

DECISION CRITERION: HIGH.

STATUS: TESTED.

## RND-RISK-007: unvalidated TTC

QUESTION: How should unvalidated TTC behave?

WHY IT MATTERS: Avoid physical promotion.

HYPOTHESIS: Tiny TTC cannot dominate.

EXPERIMENT: Change TTC only.

METRICS: Level delta.

DECISION CRITERION: Zero change.

STATUS: TESTED.

## RND-RISK-008: CPA

QUESTION: How should CPA behave?

WHY IT MATTERS: Side-pass is not crossing.

HYPOTHESIS: CPA-only change cannot dominate.

EXPERIMENT: Small/large CPA with same geometry.

METRICS: Level delta.

DECISION CRITERION: Zero change.

STATUS: TESTED.

## RND-RISK-009: unknown evidence

QUESTION: How should unknown evidence behave?

WHY IT MATTERS: Absence is not safety.

HYPOTHESIS: Missing geometry stays undetermined.

EXPERIMENT: Remove optional inputs.

METRICS: UNDETERMINED rate.

DECISION CRITERION: Never LOW.

STATUS: TESTED.

## RND-RISK-010: stale evidence

QUESTION: How should stale evidence behave?

WHY IT MATTERS: Old relevance expires.

HYPOTHESIS: Age gates remove unsupported high.

EXPERIMENT: Expire observed/source fields.

METRICS: Level, validity.

DECISION CRITERION: No indefinitely HIGH.

STATUS: TESTED.

## RND-RISK-011: fragmentation

QUESTION: How should fragmentation behave?

WHY IT MATTERS: IDs can change.

HYPOTHESIS: No automatic history inheritance.

EXPERIMENT: Replace entity ID.

METRICS: Trend.

DECISION CRITERION: UNKNOWN.

STATUS: TESTED.

## RND-RISK-012: upstream recall

QUESTION: How should upstream recall behave?

WHY IT MATTERS: Risk cannot repair invisible events.

HYPOTHESIS: Coverage remains weak.

EXPERIMENT: Same Task014 proxy windows.

METRICS: Upstream/conditional/funnel counts.

DECISION CRITERION: Show all stages and unknown denominator.

STATUS: MEASURED in report.

## RND-RISK-013: sensitivity

QUESTION: How should sensitivity behave?

WHY IT MATTERS: Avoid brittle policy.

HYPOTHESIS: Small thresholds may not affect gated inputs.

EXPERIMENT: Three fixed thresholds.

METRICS: Distributions, proxy FP/FN.

DECISION CRITERION: Report all, no selection.

STATUS: MEASURED in report.

## RND-RISK-014: trend

QUESTION: How should trend behave?

WHY IT MATTERS: No alert smoothing.

HYPOTHESIS: Immediate level changes remain visible.

EXPERIMENT: Bounded prior state.

METRICS: Trend, history size.

DECISION CRITERION: No delay or inherited identity.

STATUS: TESTED.

## RND-RISK-015: pedestrians

QUESTION: How should pedestrians behave?

WHY IT MATTERS: Class is not universal risk.

HYPOTHESIS: Geometry determines relevance.

EXPERIMENT: Class replacement and held-out review.

METRICS: Ordering, reviewed events.

DECISION CRITERION: No class-only level.

STATUS: TESTED synthetic; real UNVALIDATED.

## RND-RISK-016: bicycles

QUESTION: How should bicycles behave?

WHY IT MATTERS: Crossing matters.

HYPOTHESIS: Same geometry same level.

EXPERIMENT: Bicycle crossing fixture; draft packet.

METRICS: Level, reviewed crossings.

DECISION CRITERION: No class weight.

STATUS: TESTED synthetic; real UNVALIDATED.

## RND-RISK-017: parallel vehicles

QUESTION: How should parallel vehicles behave?

WHY IT MATTERS: Visual size is not danger.

HYPOTHESIS: Parallel below crossing.

EXPERIMENT: Outside no-intersection fixture.

METRICS: Ordering.

DECISION CRITERION: LOW below HIGH with equal quality.

STATUS: TESTED.

## RND-RISK-018: crowd

QUESTION: How should crowd behave?

WHY IT MATTERS: Identity/reference bias.

HYPOTHESIS: Proxy rates may fail in crowds.

EXPERIMENT: Review draft windows with crowd tags.

METRICS: Adjudicated event coverage.

DECISION CRITERION: Independent annotation required.

STATUS: PLANNED.

## RND-RISK-019: latency

QUESTION: How should latency behave?

WHY IT MATTERS: Reasoning must be cheap.

HYPOTHESIS: Rule stage is few-ms.

EXPERIMENT: Isolated timer in replay.

METRICS: P50/P90/P95/P99/max.

DECISION CRITERION: Separate inference/wait overhead.

STATUS: MEASURED in report.

## RND-RISK-020: scaling

QUESTION: How should scaling behave?

WHY IT MATTERS: Avoid entity-pair growth.

HYPOTHESIS: Bounded linear work.

EXPERIMENT: 1/10/50/100/128/512 stress.

METRICS: Timing, RSS, history.

DECISION CRITERION: No unbounded history or pair graph.

STATUS: MEASURED in report.
