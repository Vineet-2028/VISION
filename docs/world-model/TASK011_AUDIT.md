# Task011 adversarial audit

Pre-task READ-ONLY inspection covered Task001-010 integration, Task010 report/audit, source/frame/provenance contracts, TrackSet, exact depth sampling/geometry, flow/ego contracts, semantic/surface contracts, Guardian PoseHistory bridge, scheduler, recording, tests, dataset schema and BOM. Baseline `npm run verify` exited 0 with 511 tests. No correctly working earlier component was rewritten.

Findings during implementation and read-only inspection before corrections:

| Severity         | Affected files                | Finding and consequence                                                                 | Resolution                                                                                                        |
| ---------------- | ----------------------------- | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| HIGH             | world_model.py                | Failure metadata could retimestamp older surface/camera payload                         | Separate payload evidence from latest subsystem failure; regressions assert original identity and age             |
| HIGH             | world_model.py                | Repeated failure ticks could extend retention of old payload                            | Expire by payload observation time independently of failure status                                                |
| HIGH             | world_model.py                | Pipeline uses RECOVERABLE_FAILURE, not only FAILED                                      | Translate both statuses and public error codes; injected depth/segmentation failures tested                       |
| HIGH guarded     | world_model.py                | Wrong session, duplicate, future, reversed or mismatched frame could corrupt fusion     | Validate identity/clock before mutation, explicit watermark policy and exact depth/motion joins                   |
| CRITICAL guarded | world_model.py/world_types.py | Draft semantics or relative depth could become trusted metric facts                     | UNVERIFIED always preserved; no relative metric point; exact pose/depth and Guardian geometry tests               |
| MEDIUM           | world_config.py               | Freshness defaults affect retained availability                                         | Explicit provisional configuration and measured source ages; no safety qualification                              |
| MEDIUM           | inherited perception          | Track fragmentation, noisy depth, draft semantics, CPU contention and checkpoint rights | Limits retained; no re-identification or accuracy claims                                                          |
| LOW              | world_types.py                | Regions are bounded boxes, not persistent projected surfaces                            | Explicit image-space contract; optional calibrated projection is tested; real footage lacks a supplied plane/pose |

No raw footage upload, external telemetry, biometric identity, plate identity, navigation or risk state. Source paths are excluded from public measurement configuration. Original observations are unchanged. Serial identity is scoped to a local session. All tests and measurements must be reported as executed, pending or unverified in the results document.

Additional HIGH correction: late object depth cannot overwrite a newer subsystem failure status. A regression test preserves the failure while retaining old object depth as stale. Analytical Guardian tests cover bearing and supplied plane projection; projection remains unverified, never a trusted ground fact.

Final verification exposed an additional HIGH boundary issue: Task008 permits a point tagged UNKNOWN calibration, while world position publication requires supported camera calibration. World-model camera-point derivation now requires VALID or DEGRADED calibration. A metric depth estimate may still be available without a position; its capability remains explicitly unvalidated. The regression now passes. The first final verify stopped at this test; the second full run is the final verification evidence.
