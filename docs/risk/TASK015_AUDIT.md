# Task015 adversarial audit

Read-only pre-task review inspected WorldState/WorldEntity, corridor/trajectory/interaction contracts, Guardian ownership, source clocks, quality/physical-validity states, scheduler, recording, benchmark censoring, Task014 results and replacement contracts. `packages/risk-engine` was a placeholder; no existing runtime owned risk. Prior full verification recorded 732 tests. Missing geometry remained explicitly unknown; this task must not reinterpret it as safety.

CRITICAL implementation gates: insufficient evidence is UNDETERMINED; no scene-safe field; no physical promotion; TTC/CPA diagnostic only; current occupancy independent of TTC; no duplicated geometry; bounded expiry; predicted tracks not observations; unverified semantics preserved; no class-only levels; no alerting; upstream 5.8% visible; proxy conditional results distinguished from full recall; bounded history.

HIGH implementation checks: quality separate from level; explainable reasons; fixed development thresholds; new identities do not inherit history; optional injection and schema 10 recording; current occupancy retained when future evidence fails. Source freshness checks include corridor heading and relation sources, not merely wrapper timestamps. EvidenceSource quality strings include descriptive uncalibrated labels, so explicit status/time gates are used rather than assuming every usable source says GOOD.

MEDIUM remaining research limits: weak upstream recall and identity, unknown real hazard denominator, unreviewed risk labels, frozen corridor/point-path assumptions, uncertain thresholds, unqualified crowd/body-motion/low-light performance and upstream cadence. These block safety qualification, not prototype software experimentation. LOW: debug panel displays only a bounded subset and threshold names remain research policy.

No production dependency, network inference, telemetry or biometric identity is added. Review server is loopback/read-only. Local footage/artifacts remain ignored. Executed results and any repaired defects are recorded in the dated completion report; no independent human validation is claimed.

Post-implementation fixes and evidence:

- `risk.py`: unknown alternative forecasts now prevent LOW, and forecasts without their own fresh corridor relation cannot borrow another entity's valid relation. Regression tests cover unknown alternatives and stale relation sources.
- `risk.py`: provenance uses the named configuration-hash field rather than overloading component type. The immutable-output test verifies both fields.
- `risk_benchmark.py`: independent-process timing showed 42.8% and 33.6% slower full runs, despite less than one second of measured risk-stage work. These unfavorable results are retained. A same-process disabled/enabled/enabled/disabled control stayed within the provisional 5% overhead gate; its apparent speedup is not claimed as a causal benefit. Machine/warm-up variation and target-device throughput remain qualification limits.
- `README.md`: the overview now separates the current prototype from planned mobile/audio components and removes unsupported current real-time/physical-risk implications.

See the [A–AU completion report](../research/results/task015-risk-2026-10-24.md) for exact counts, timing distributions, the proxy funnel and remaining risks. No reviewed human hazard denominator exists.

Final verification on 2026-10-24: `npm.cmd run verify` exited 0. All 778 tests passed (193 Guardian, 558 perception-lab, 24 web, 3 API), together with formatting, linting, strict type checking, Spotless/SpotBugs, production builds, dependency audit and runtime smoke checks. The dependency gate reported no npm advisories. The log is preserved locally at `benchmark-results/task015/verify.log`; initial verification is preserved separately. Final report/manifest formatting and `git diff --check` also passed. Hosted CI and target hardware were not executed.
