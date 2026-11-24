# Task001–018 integration audit

Task018 is an evaluation consumer. No intelligence policy, threshold, model or production framework is changed. PASS below means contract compatibility, not physical correctness. Final executed regression evidence belongs in the Task018 result report; historical passes are not represented as fresh executions.

| Boundary                 | Status  | Evidence and limits                                                                   |
| ------------------------ | ------- | ------------------------------------------------------------------------------------- |
| 001 → 002                | PASS    | Existing web/API and core contracts unchanged; prior integration baseline retained.   |
| 002 → 003                | PASS    | Calibration ownership unchanged; absent calibration remains explicit.                 |
| 003 → 004                | PASS    | Media/monotonic clock boundary retained; evaluation records both.                     |
| 004 → 005                | PASS    | Replay scheduling and bounded queue unchanged.                                        |
| 005 → 006                | PASS    | Model adapters still publish normalized immutable detection outputs.                  |
| 006 → 007                | PARTIAL | Detection/track linkage is readable; prototype identity quality remains weak.         |
| 007 → 008                | PARTIAL | Track IDs and depth evidence join; physical range remains unvalidated.                |
| 008 → 009                | PARTIAL | Relative depth never becomes metric motion authority.                                 |
| 009 → 010                | PARTIAL | Motion and semantic timing preserved; calibration/semantic truth unavailable.         |
| 010 → 011                | PASS    | WorldState exposes normalized evidence and explicit quality/ages.                     |
| 011 → 012                | PARTIAL | Corridor consumes WorldState; image fallback is not body heading or ground truth.     |
| 012 → 013                | PARTIAL | Frozen corridor and trajectories share IDs/units; future motion accuracy unvalidated. |
| 013 → 014                | PARTIAL | Interaction joins forecasts; historical 5.8% tracker-proxy recall retained.           |
| 014 → 015                | PARTIAL | Risk consumes forecasts without recomputing physical geometry; source coverage weak.  |
| 015 → 016                | PASS    | Attention retains risk quality, identity, expiry and unknown semantics.               |
| 016 → 017                | PASS    | Alert layer consumes selected decisions and rejects expiry; no policy reranking.      |
| 017 → 018                | PARTIAL | New measurements cover candidate ages; old 3579 candidate ages cannot be recovered.   |
| Source annotations → 018 | PARTIAL | Hash-checked prototype references and blind drafts; no independent hazard truth.      |
| 018 → research reports   | PASS    | Separate strata, coherent prefix denominators, one primary failure and null unknowns. |
| 018 → future rescue      | PASS    | Bounded experiments and measured priorities only; no rescue implementation here.      |

## Ownership and replacement

Pure typed `v0_evaluation.py` contains immutable evaluation contracts and reference accounting only. The tools own file I/O, local video review, model construction and measurement instrumentation. Production pipeline, domain policies and API/web do not import evaluation tools. Dataclass runtime outputs are consumed without adding detector classes to domain contracts. Reference classification never writes into runtime confidence or physical validity.

Alternative detector support in the benchmark constructor is currently limited to the existing PicoDet/YOLOX adapters. Other runtime providers remain replaceable through their production protocols but have not been qualified by this canonical measurement. An unknown model runtime must fail explicitly rather than silently selecting a fallback. The benchmark is not a new production orchestration framework.

## Adversarial inspection

HIGH measurement risks addressed during implementation: mismatched source references now fail closed; a downstream success cannot resurrect a failed upstream path; existing reviewed packets cannot silently become drafts; incomplete runs cannot receive scores; earliest stage observations are retained rather than replaced by a later longer path. Relevant occupancy events are matched only during their relevant reference observations. Regression tests exercise these accounting boundaries.

MEDIUM remaining: prototype reference IDs are not independent identity truth; annotation matching has a 100 ms tolerance; oldest evidence and current-frame publication age are different quantities; raw trace component names are omitted; large private JSONL creates non-negligible I/O; ablation is one fixed-order pass. These are disclosed measurement limits, not reasons to relax runtime expiry. No new CRITICAL runtime issue was found by this Task018-focused inspection; this is not a certification of all possible paths.

Privacy: no automatic telemetry, cloud upload or review logging added. The review server binds loopback and uses the existing route allowlist. Raw video, local paths and event traces remain in ignored local directories. Committed reports contain aggregate measurements only.
