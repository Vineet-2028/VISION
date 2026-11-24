# Quality and capabilities

IMPLEMENTED capability-specific states: HAS_TRACKING, HAS_METRIC_DEPTH_ESTIMATE, HAS_CAMERA_POSE, HAS_SEMANTIC_SURFACE, HAS_MOTION_EVIDENCE. Each exposes status and reason codes. Non-null historical data is not a current capability guarantee. Fresh metric estimates are still DEGRADED/unvalidated research values. Missing metric depth does not erase image-space tracks. HAS_METRIC_DEPTH_ESTIMATE refers to a value, not an available camera/world position: UNKNOWN calibration can retain a model depth value while position remains unavailable.

WorldSceneQuality conservatively reports DEGRADED when some entity/surface evidence exists and UNRELIABLE when no such state is established, with explicit subsystem reasons. It does not average confidences or output safety probability. There is no calibrated covariance; original uncertainty statuses remain UNKNOWN where unavailable.

Important reasons: DEPTH_STALE, TRACK_PREDICTED_ONLY, WORLD_POSITION_UNAVAILABLE, POSE_DEPTH_TIME_MISMATCH, SEMANTIC_UNVERIFIED, SOURCE_FAILURE, source-specific unavailable/stale states and bounded conflict diagnostics. Camera motion retains scale status NONE / UP_TO_SCALE / DEPTH_SCALED_RESEARCH. Neither image rates nor scale direction are physical object velocity.

UNVALIDATED: semantic ground truth, model metric distance, physical ego/object motion, global localization, safety and production use. Local engineering acceptance does not change these labels. PROVISIONAL: identity continuity and freshness thresholds. PLANNED: probabilistic fusion only after suitable measurement/uncertainty evidence exists.
