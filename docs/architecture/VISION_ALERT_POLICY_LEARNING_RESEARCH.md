# Optional alert utility research

The deterministic Guardian remains authoritative. No live reinforcement learning,
exploration or autonomous suppression of credible risk is permitted in this pass.
An unlogged, unspoken alert has no reliable counterfactual usefulness label. A user
rating alone cannot identify whether silence would have been safe.

Independent reviewers label relevance, timing, motion and interruption class:
MUST_NOTIFY (credible hazard), OPTIONAL (informational context), SILENCE (irrelevant
interruption), UNAVAILABLE (capability notice), UNKNOWN (insufficient context).
For example, a credible imminent collision and lost camera capability are mandatory;
a nonurgent object description may be optional. These are review classes, not new
risk thresholds. Disagreement blocks manifest publication until reconciled.

`evaluate_optional_ranking` provides a paired offline harness: mandatory suppression,
unnecessary interruptions, optional omissions, unknown labels and abstention counts.
It always emits SHADOW_ONLY, training_performed=false and promotion_allowed=false.
A zero suppression count is only a software gate on the supplied sample, never
proof of safety. Missing decisions abstain to the deterministic baseline.

Future supervised preference work must freeze independently reviewed grouped data
and compare baseline/candidate on the same examples. Treat mandatory misses as a
hard veto, not a finite reward tradeoff; compare optional interruption utility only
after that veto. Report uncertainty and scenario coverage, not an aggregate score
that hides unknowns. Independently record candidate latency and stale decisions.
Ranking could only reorder optional information within the remaining freshness
budget; mandatory alerts, unavailable notices and evidence expiry remain outside
its control. Run offline and shadow-only before any separate physical trial.
