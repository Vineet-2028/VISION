# Task001-009 integration audit

Engineering boundary audit for local research. Accuracy/safety qualification remains separate.

| Boundary                                         | Status  | Evidence / limitation                                                      |
| ------------------------------------------------ | ------- | -------------------------------------------------------------------------- |
| 001 -> 002                                       | PASS    | Independent Guardian build/tests retained                                  |
| 002 -> 003                                       | PASS    | Guardian remains authoritative geometry                                    |
| 003 -> 004                                       | PASS    | Spatial frames and source clocks unchanged                                 |
| 004 -> 005                                       | PASS    | PTS separated from processing time                                         |
| 005 -> 006                                       | PASS    | Existing DetectionBatch and runtime selection retained                     |
| 006 -> 007                                       | PASS    | Tracker remains detector-independent                                       |
| 007 -> 008                                       | PASS    | Exact observed-box depth association unchanged                             |
| 008 -> 009                                       | PASS    | Exact frame-A metric research path; relative/stale depth rejected          |
| 003 -> 009                                       | PASS    | Guardian undistortion, projection and affine restoration; analytical tests |
| 004 -> 009                                       | PASS    | Explicit pair/session; Task004 pose history and camera mount bridge        |
| 006 -> 009                                       | PASS    | Optional generic masks; real PicoDet/YOLOX offline replacement runs        |
| 007 -> 009                                       | PASS    | Generic TrackSet sampling; predicted-only exclusion; no tracker rewrite    |
| Real video -> physical pose                      | PARTIAL | Placeholder calibration, no trajectory truth or synchronized IMU           |
| Local prototype -> real-time assistive operation | PARTIAL | Measured CPU/freshness limitations; no safety qualification                |

Depth/PnP and IMU paths are explicit research APIs. Default CLI uses visual motion and does not silently fuse cached depth/IMU. Future segmentation supplies optional SemanticExclusion; future VIO supplies EgoMotionEstimator. Future world reasoning can join track/depth/motion using explicit source/session/time without knowing detector/depth/flow algorithms. Such future consumers are not implemented here.
