# Ego-motion architecture

IMPLEMENTED: replaceable EgoMotionEstimator protocol, VisualEgoEstimator, ImuRotationEstimator and explicit DepthAssistedEgoEstimator research path. Pipeline defaults to visual estimation; frame-A depth and synchronized IMU must be injected explicitly through their APIs. No implicit latest-depth cache or latest-pose lookup.

Static-point convention is X_B = R_BA X_A + t_BA. This is a coordinate transform, not the camera's travel vector. Essential matrix recovery supplies only a unit translation direction with UP_TO_SCALE. NONE contains no translation. DEPTH_SCALED_RESEARCH carries a separate research translation and depth-provider provenance. It is UNVALIDATED_SCALE, never trusted odometry.

Guardian supplies undistorted calibrated rays and projections. Visual estimation uses normalized coordinates, bounded rotation RANSAC, Essential RANSAC and a homography-support diagnostic. Pure-rotation/low-parallax observations return rotation without translation. Planar dominance conservatively returns unavailable. Inlier spatial coverage is checked. All visual results remain DEGRADED because static-majority/calibration assumptions are unvalidated.

PnP uses only exact frame-A metric Z/range depth. Relative or wrong-frame depth raises; inadequate and degenerate geometry returns unavailable. This path is an explicit research API, not enabled automatically by slow scheduled depth. Rotation compensation is available without depth. Future VIO/SLAM can implement the same estimator protocol; no full mapping, loop closure, ESKF, physical object velocity or risk logic is implemented.

Calibration gate: UNKNOWN/INVALID calibration cannot produce visual ego-motion, research PnP or projected compensation. The available real recording uses an identity-only UNKNOWN calibration, so real camera-motion/residual metrics are unavailable. Analytical tests use explicit synthetic valid geometry. Supply measured calibration before interpreting real camera-motion evidence.
