# Task001–008 integration audit

Task007 was accepted for prototype integration, not independent identity accuracy.
This audit concerns implemented boundaries, not production assistive qualification.

| Boundary                             | Status  | Evidence / limitation                                                                                              |
| ------------------------------------ | ------- | ------------------------------------------------------------------------------------------------------------------ |
| 001 -> 002                           | PASS    | Independent Java core still built and checked by root scripts.                                                     |
| 002 -> 003                           | PASS    | Guardian remains the spatial math authority.                                                                       |
| 003 -> 004                           | PASS    | Explicit spatial frames and observation clocks retained.                                                           |
| 004 -> 005                           | PASS    | Source observation PTS remains distinct from processing clock.                                                     |
| 005 -> 006                           | PASS    | DetectionBatch remains vendor-independent and camera-coordinate based.                                             |
| 006 -> 007                           | PASS    | Depth does not modify detector/tracker contracts or TrackId.                                                       |
| 007 -> 008                           | PASS    | Exact-frame observed-box association; predicted/unavailable distinction tested.                                    |
| 003 -> 008                           | PASS    | Java image mappings, calibrated rays, Z/range and transform composition tested.                                    |
| 004 -> 008                           | PASS    | Exact pose/frame identity required; no latest-pose substitution.                                                   |
| Real calibration -> physical ranging | PARTIAL | Current recording has placeholder calibration and no metric ground truth.                                          |
| 008 -> 009                           | PASS    | Contracts, real-provider comparisons, final replay and full verification complete for local prototype integration. |

Vendor imports stay inside depth_runtime.py. Guardian/web/API do not depend on
Transformers, torch or Python depth values. NumPy dense arrays are lab-owned storage,
not vendor output objects; downstream consumers use DepthFrame/DepthEstimate.
No dependency was added. Runtime models are optional existing research dependencies.

Depth recording uses summary schema3 and excludes dense maps before dataclass
serialization. Source pixels and depth maps are not stored in track histories.
Default association has no carry-forward state, so object identities cannot silently
inherit old depth histories. An undetected wrong TrackId remains a tracking limitation.

The whole pipeline is single-owner and synchronous. Independent scheduler cadence
does not mean parallel inference. Slow depth can delay tracking/detection; measured
result age and explicit unavailable output are required. No throughput guarantee.
