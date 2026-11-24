# Canonical V0 benchmark snapshot

Task018, 2026-10-25. Local prototype engineering; one source and one Windows host.

| Mode     | Processed | Dropped | Failures | Text accepted | Pipeline seconds | Including setup seconds |
| -------- | --------- | ------- | -------- | ------------- | ---------------- | ----------------------- |
| Offline  | 18000     | 1       | 0        | 60            | 3106.501         | 3144.303                |
| Realtime | 62        | 17939   | 0        | 0             | 605.079          | 644.286                 |

| Stage             | Offline conditional | Realtime conditional |
| ----------------- | ------------------- | -------------------- |
| DETECTION         | 182/188             | 12/188               |
| TRACK             | 177/182             | 12/12                |
| WORLD             | 177/177             | 12/12                |
| CORRIDOR          | 176/177             | 12/12                |
| TRAJECTORY        | 176/176             | 12/12                |
| INTERACTION       | 176/176             | 12/12                |
| RISK              | 166/176             | 12/12                |
| ATTENTION         | 1/166               | 0/12                 |
| ALERT_INTENT      | 1/1                 | 0/0                  |
| VALID_ALERT       | 1/1                 | 0/0                  |
| DELIVERABLE_ALERT | 1/1                 | 0/0                  |

| Dimension        | Status      | Evidence                                                                               |
| ---------------- | ----------- | -------------------------------------------------------------------------------------- |
| Architecture     | STRONG      | Normalized immutable boundaries and full regression gate; limited to engineering scope |
| Offline loop     | STRONG      | 18,000 frames, 60 text outputs, no processing failures                                 |
| Realtime         | WEAK        | Zero accepted text; stale before reasoning; 61 tracking gap resets                     |
| Coverage         | WEAK        | 1/188 occupancy-proxy events delivered; not hazard recall                              |
| Identity         | WEAK        | Historical ID errors and current cadence resets                                        |
| Reproducibility  | PARTIAL     | Frozen hashes/config/seed; one Windows machine and one source; model files local       |
| Human usefulness | UNVALIDATED | No adjudicated blind event labels or user study                                        |
| Physical safety  | UNVALIDATED | No independent metric motion/range or safety qualification                             |

Historical facts: Task014 forecast-entry proxy 3/52=5.8%; Task016 conditional episode 60/1507=3.98%; Task0173579 expired/0 live. These populations and configurations differ and must not be merged. New Task0181239 expired/0 live; full offline 60 text outputs. New occupancy proxy 1/188 offline is not hazard recall.

Realtime publication intervals: P50=9744.943 ms; P90=10777.903 ms; P95=11001.493 ms; P99=12401.919 ms; max=12401.919 ms (n=61). Pure reasoning P95 7.579ms.

Tests: Task006C383; Task009480; Task011558; Task015778; Task016824; Task0171222; Task0181242. These are dated report counts, not safety scores.

Reproduce: `npm.cmd run evaluate:v0 -- --config <approved-local-config.json> --output <new-output-directory>`. Read [protocol](../../evaluation/V0_EVALUATION_PROTOCOL.md) before interpreting clocks, denominators or ablations. Full [56-section report](task018-v0-2026-10-25.md) and [JSON](task018-v0-2026-10-25.json).

NEXT_PHASE: V0_RESCUE_PASS. No Task019. No realtime, human-usefulness, physical-accuracy or production-safety qualification.
