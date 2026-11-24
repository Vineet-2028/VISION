# Task001-017 integration audit

Scope: local prototype software engineering. Task016 implemented for prototype research. Refer to Task013 integration audit for prior boundary evidence; current full verification is reported separately.

| Boundary   | Status  | Evidence / limitation                                                                                        |
| ---------- | ------- | ------------------------------------------------------------------------------------------------------------ |
| 001 -> 002 | PASS    | Existing normalized contract preserved; full repository regression checks passed.                            |
| 002 -> 003 | PASS    | Existing normalized contract preserved; full repository regression checks passed.                            |
| 003 -> 004 | PASS    | Existing normalized contract preserved; full repository regression checks passed.                            |
| 004 -> 005 | PASS    | Existing normalized contract preserved; full repository regression checks passed.                            |
| 005 -> 006 | PASS    | Existing normalized contract preserved; full repository regression checks passed.                            |
| 006 -> 007 | PASS    | Existing normalized contract preserved; full repository regression checks passed.                            |
| 007 -> 008 | PASS    | Existing normalized contract preserved; full repository regression checks passed.                            |
| 008 -> 009 | PASS    | Existing normalized contract preserved; full repository regression checks passed.                            |
| 009 -> 010 | PASS    | Existing normalized contract preserved; full repository regression checks passed.                            |
| 010 -> 011 | PASS    | Existing normalized contract preserved; full repository regression checks passed.                            |
| 011 -> 012 | PASS    | Existing normalized contract preserved; full repository regression checks passed.                            |
| 012 -> 013 | PASS    | Immutable WorldState/CorridorAnalysis consumed by optional TrajectoryPredictor; schema8 recording and tests. |
| 004 -> 013 | PASS    | Authoritative nanoseconds, irregular dt and Guardian nominal metric prediction.                              |
| 007 -> 013 | PARTIAL | Observed histories only; identity corruption remains an upstream research limitation.                        |
| 008 -> 013 | PARTIAL | Relative-depth rejection and exact metric/pose gating tested; physical depth remains unvalidated.            |
| 009 -> 013 | PARTIAL | Residual hypothesis is separate; future camera trajectory and physical motion unavailable.                   |
| 011 -> 013 | PASS    | Bounded immutable history, exact source joins, no prediction feedback.                                       |
| 012 -> 013 | PARTIAL | Image frozen-corridor entry implemented; metric/bearing interaction mapping explicitly unknown.              |

These PARTIAL statuses are evidence/representation limits, not permission to relabel research output as physical truth. No production-safety qualification follows from software checks.

## Task014 boundaries

| Boundary   | Status  | Evidence / limitation                                                                                  |
| ---------- | ------- | ------------------------------------------------------------------------------------------------------ |
| 013 -> 014 | PASS    | Immutable source-matched trajectories, horizon enforcement, predictor swaps and recording tests.       |
| 002 -> 014 | PASS    | Actual Guardian TTC/CPA bridge, signed past query, analytical fixtures; no duplicate Python equations. |
| 004 -> 014 | PASS    | Matching source times/clocks; future/mixed source rejection; no wall-clock evidence.                   |
| 007 -> 014 | PARTIAL | Session-local IDs, no retained interaction history; inherited identity errors remain.                  |
| 008 -> 014 | PARTIAL | Metric gates and relative-depth rejection pass; real depth accuracy unvalidated.                       |
| 009 -> 014 | PARTIAL | Explicit reference limitation; no validated real user velocity or ego scale.                           |
| 011 -> 014 | PASS    | Stateless bounded WorldState consumer, schema and source checks.                                       |
| 012 -> 014 | PARTIAL | Image/world-plane geometry implemented; frozen corridor and bearing polygon mapping limits explicit.   |

PASS means local software compatibility, not physical validation. Task015 policy is now covered below; Task016 policy is audited below.

## Task015 boundaries

| Boundary   | Status  | Evidence / limitation                                                                                           |
| ---------- | ------- | --------------------------------------------------------------------------------------------------------------- |
| 011 -> 015 | PASS    | Immutable world contract, observed/source age gates, capabilities and bounded identity history.                 |
| 012 -> 015 | PARTIAL | Current occupancy supported, source heading/relation freshness checked; corridor heuristic remains unvalidated. |
| 013 -> 015 | PARTIAL | Timestamp/quality gates and no new trajectory generation; unreliable paths cannot imply LOW.                    |
| 014 -> 015 | PARTIAL | Geometry-only consumer, diagnostic TTC/CPA, 5.8% coverage ceiling explicit; no physical qualification.          |
| 015 -> 016 | PASS    | Immutable documented contract and injected-engine recording test; attention implementation audited below.       |

Prior PASS statuses refer to software boundaries/regressions, not fresh independent
physical qualification. Vendor model combinations and target hardware remain unverified.

## Task016 boundaries

| Boundary          | Status  | Evidence / limitation                                                                                                                                                      |
| ----------------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 004 -> 016        | PASS    | State nanoseconds only; duplicate/out-of-order/session/seek regression tests.                                                                                              |
| 007/011 -> 016    | PARTIAL | Stable session/entity contract passes; physical identity continuity remains imperfect.                                                                                     |
| 014 -> 016        | PARTIAL | Risk-provided reason context only; inherited 5.8% proxy recall and physical limits retained.                                                                               |
| 015 -> 016        | PASS    | Immutable risk contract, quality separate from level, injected policy and alternative producer tests.                                                                      |
| 016 -> recording  | PASS    | Additive schema11; automatic dataclass serialization and cleanup regression.                                                                                               |
| 016 -> future 017 | PASS    | Semantic modality-independent contract documented; nullable category/direction, expiry and busy/preemption intent. Task017 contract implemented; see new boundaries below. |

PASS describes software compatibility; human usefulness, hazard recall and physical safety remain unvalidated.

Final verification: 824 tests and `npm.cmd run verify` passed on 2026-10-24. See the [Task016 report](../research/results/task016-attention-2026-10-24.md) for measured limits and unverified items.

## Task017 boundaries

| Boundary          | Status  | Evidence / limitation                                                                                          |
| ----------------- | ------- | -------------------------------------------------------------------------------------------------------------- |
| 004 -> 017        | PASS    | Media-mapped realtime clock, expiry at render/accept/consume, seek/session tests.                              |
| 011 -> 017        | PARTIAL | Stable entity/session references; physical identity continuity remains imperfect.                              |
| 015 -> 017        | PARTIAL | Risk provenance/quality/ages pass through attention; category/direction not yet authorized by actual producer. |
| 016 -> 017        | PASS    | Selected immutable attention only; silence/expiry/dedup/swap tests. No reranking.                              |
| 017 -> recording  | PASS    | Additive schema12, frozen outputs, cleanup and serialization tests.                                            |
| 017 -> future 018 | PASS    | Recorded evaluation contract documented; Task018 implementation not started.                                   |

Prior test totals above are dated Task016 evidence, not the Task017 final count.
Final Task017 execution and limitations are in docs/research/results/task017-alerts-2026-10-25.md.
PASS means software compatibility, not physical or human validation.
