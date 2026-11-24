# Trajectory research register

All physical/safety validation remains UNVALIDATED. Executed metrics are linked from the Task013 results report; synthetic and tracker-proxy experiments are not independent physical truth.

## RND-TRAJ-001 — CP versus CV

QUESTION: How does cp versus cv affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use deterministic fixtures and bounded benchmark/replay measurements.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: IMPLEMENTED experiment; measured results in Task013 report.

## RND-TRAJ-002 — Last-two versus window fit

QUESTION: How does last-two versus window fit affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use deterministic fixtures and bounded benchmark/replay measurements.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: IMPLEMENTED experiment; measured results in Task013 report.

## RND-TRAJ-003 — CV versus acceleration

QUESTION: How does cv versus acceleration affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use separately reviewed sequences with controlled variations; synthetic gating tests do not substitute for that study.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: DEFERRED; acceleration cases expose baseline limits, no CA selected.

## RND-TRAJ-004 — History window size

QUESTION: How does history window size affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use separately reviewed sequences with controlled variations; synthetic gating tests do not substitute for that study.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: PLANNED independent qualification; contract/fixture coverage is not accuracy validation.

## RND-TRAJ-005 — Irregular timestamps

QUESTION: How does irregular timestamps affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use deterministic fixtures and bounded benchmark/replay measurements.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: IMPLEMENTED experiment; measured results in Task013 report.

## RND-TRAJ-006 — Outlier robustness

QUESTION: How does outlier robustness affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use deterministic fixtures and bounded benchmark/replay measurements.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: IMPLEMENTED experiment; measured results in Task013 report.

## RND-TRAJ-007 — Stationary hypothesis

QUESTION: How does stationary hypothesis affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use deterministic fixtures and bounded benchmark/replay measurements.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: IMPLEMENTED experiment; measured results in Task013 report.

## RND-TRAJ-008 — Raw versus compensated image motion

QUESTION: How does raw versus compensated image motion affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use separately reviewed sequences with controlled variations; synthetic gating tests do not substitute for that study.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: IMPLEMENTED alternate residual hypothesis; comparison is a raw-view mismatch diagnostic, stabilized-view truth remains PLANNED.

## RND-TRAJ-009 — Bearing trajectory

QUESTION: How does bearing trajectory affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use separately reviewed sequences with controlled variations; synthetic gating tests do not substitute for that study.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: PLANNED independent qualification; contract/fixture coverage is not accuracy validation.

## RND-TRAJ-010 — World-research stability

QUESTION: How does world-research stability affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use separately reviewed sequences with controlled variations; synthetic gating tests do not substitute for that study.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: PLANNED independent qualification; contract/fixture coverage is not accuracy validation.

## RND-TRAJ-011 — Depth jitter

QUESTION: How does depth jitter affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use separately reviewed sequences with controlled variations; synthetic gating tests do not substitute for that study.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: PLANNED independent qualification; contract/fixture coverage is not accuracy validation.

## RND-TRAJ-012 — Track fragmentation

QUESTION: How does track fragmentation affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use separately reviewed sequences with controlled variations; synthetic gating tests do not substitute for that study.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: PLANNED independent qualification; contract/fixture coverage is not accuracy validation.

## RND-TRAJ-013 — Crowd behavior

QUESTION: How does crowd behavior affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use separately reviewed sequences with controlled variations; synthetic gating tests do not substitute for that study.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: PLANNED independent qualification; contract/fixture coverage is not accuracy validation.

## RND-TRAJ-014 — Small-object jitter

QUESTION: How does small-object jitter affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use separately reviewed sequences with controlled variations; synthetic gating tests do not substitute for that study.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: PLANNED independent qualification; contract/fixture coverage is not accuracy validation.

## RND-TRAJ-015 — Horizon error

QUESTION: How does horizon error affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use deterministic fixtures and bounded benchmark/replay measurements.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: IMPLEMENTED experiment; measured results in Task013 report.

## RND-TRAJ-016 — Uncertainty growth

QUESTION: How does uncertainty growth affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use deterministic fixtures and bounded benchmark/replay measurements.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: IMPLEMENTED experiment; measured results in Task013 report.

## RND-TRAJ-017 — Frozen corridor entry

QUESTION: How does frozen corridor entry affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use deterministic fixtures and bounded benchmark/replay measurements.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: IMPLEMENTED experiment; measured results in Task013 report.

## RND-TRAJ-018 — Compute latency

QUESTION: How does compute latency affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use deterministic fixtures and bounded benchmark/replay measurements.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: IMPLEMENTED experiment; measured results in Task013 report.

## RND-TRAJ-019 — Many-entity scaling

QUESTION: How does many-entity scaling affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use deterministic fixtures and bounded benchmark/replay measurements.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: IMPLEMENTED experiment; measured results in Task013 report.

## RND-TRAJ-020 — Future learned models

QUESTION: How does future learned models affect short-horizon prediction?

WHY IT MATTERS: Prevent unsupported trajectory quality and preserve predictable runtime/fallback behavior.

HYPOTHESIS: A bounded simple baseline can expose this limitation before adding complexity.

EXPERIMENT: Use separately reviewed sequences with controlled variations; synthetic gating tests do not substitute for that study.

METRICS: Per-horizon displacement, unavailable/reset rate, residual/error, and compute latency with explicit domain units.

DECISION CRITERION: Accept a change only if it improves held-out error or robustness without violating causality, units, boundedness or latency; no physical claim from proxy labels.

STATUS: PLANNED independent qualification; contract/fixture coverage is not accuracy validation.
