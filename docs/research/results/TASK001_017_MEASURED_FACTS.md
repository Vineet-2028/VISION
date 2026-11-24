# Task001–017 measured facts (pre-Task018 audit)

These are historical measurements, not a new qualification run. Runs used different task-era configurations and are not direct apples-to-apples performance comparisons. No source hazard truth is inferred from model outputs.

| Fact                                 | Recorded value                                     | Source / status                                                         |
| ------------------------------------ | -------------------------------------------------- | ----------------------------------------------------------------------- |
| Task006C verification                | 383 tests                                          | task006c-reviewed-2026-10-18.md; software                               |
| Task007 prototype identity F1        | approximately 0.274                                | task007-prototype-accepted-2026-10-18.md; accepted prototype references |
| Task007 ID switches                  | 2091                                               | same report; not independent human identity qualification               |
| Task008 depth execution P95          | 1311.05 ms                                         | task008-depth-2026-10-19.md; local replay                               |
| Task009 sampled motion run           | 1199 pairs; 600 source seconds                     | task009-motion-2026-10-19.md; calibration unavailable                   |
| Task010 semantic run                 | 600 updates; 1014.55 wall seconds                  | task010-semantics-2026-10-21.md; 1 Hz sampled, not realtime             |
| Task011 all-real realtime            | 68 world updates / 600 source seconds              | task011-world-model-2026-10-21.md; task-era config                      |
| Task012 realtime                     | 482 updates / 600 source seconds                   | task012-corridor-2026-10-22.md; task-era config                         |
| Task014 tracker-proxy entry recall   | 5.8%                                               | task014-interactions-2026-10-23.md; conditional tracker proxy           |
| Task015 proxy reproduction           | TP3 / (TP3 + FN49)                                 | task015-risk-2026-10-24.md; stable-ID window subset                     |
| Task016 conditional episode coverage | 60 / 1507 = 3.98% rounded                          | task016-attention-2026-10-24.md; not hazard recall                      |
| Task016 packet                       | 30 draft windows; 900 updates; 180 sampled seconds | same report; no reviewed interaction truth                              |
| Task017 verification                 | 1222                                               | task017-alerts-2026-10-25.json; automated tests, not safety             |
| Task017 realtime processed           | 157                                                | task017-alerts-2026-10-25.json; 600 source seconds                      |
| Task017 realtime dropped             | 17844                                              | task017-alerts-2026-10-25.json; latest-frame/staleness                  |
| Task017 realtime failed              | 0                                                  | task017-alerts-2026-10-25.json; processing failures                     |
| Task017 realtime wall seconds        | 601.0461263                                        | task017-alerts-2026-10-25.json; local run                               |
| Task017 expired candidates           | 3579                                               | task017-alerts-2026-10-25.json; upstream candidates, not unique hazards |
| Task017 live text accepted           | 0                                                  | task017-alerts-2026-10-25.json; zero; audio not implemented             |
| Task017 offline text outputs         | 60                                                 | task017-alerts-2026-10-25.json; frozen Task016 decisions; not live      |

Task017 full verification reported no npm advisories. Earlier Task014 reports retained five reviewed development advisory entries; this historical discrepancy must be checked against the current gate, not hidden or assumed unchanged. Physical accuracy, semantic/risk truth, hazard recall, human usefulness and production safety remain unvalidated.

Dataset manifest schema3 contains458 images and3 temporal split records from one underlying source hash. Tracking prototype references contain300 frames across3 clips. Their review flags do not establish independent interaction-relevance truth.

The old Task017 realtime artifact contains aggregate stage distributions and alert diagnostics but no per-candidate source-age trace. Exact ages for those3579 candidates cannot be reconstructed; new instrumentation must measure a new run without overwriting the historical counts.
