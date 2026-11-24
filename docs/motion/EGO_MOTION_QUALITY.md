# Motion quality

IMPLEMENTED diagnostics: feature count, forward/backward error and validity, 4x4 spatial coverage, inlier count/ratio, homography support, residual error where available, pair gap, calibration status and explicit degeneracy reason. These are not calibrated probabilities.

Reasons include INSUFFICIENT_FEATURES, POOR_SPATIAL_DISTRIBUTION, CALIBRATION_UNAVAILABLE, PLANAR_DOMINANT, RANSAC_FAILURE, LOW_PARALLAX_OR_DYNAMIC_SCENE, PURE_ROTATION_LIKELY_OR_LOW_PARALLAX, DEPTH_INSUFFICIENT, DEGENERATE_DEPTH_GEOMETRY and IMU_UNAVAILABLE. Semantic exclusions leaving too few points can report DYNAMIC_SCENE_DOMINANT. Unmasked points are static-background candidates only. Detector misses/failures do not prove a static scene.

All available visual/PnP estimates are DEGRADED in this prototype. Unavailable transforms produce no compensated residual, rather than fabricated zero motion. Pure rotation and low parallax are deliberately not over-separated. A coherent dynamic majority is fundamentally ambiguous without additional evidence; current logic does not claim reliable detection of every such scene.

UNVALIDATED: physical pose accuracy, metric scale, safety, night/crowd performance, rolling-shutter compensation and calibrated uncertainty. Research decisions must retain these limitations downstream.

Calibration gate: UNKNOWN/INVALID calibration cannot produce visual ego-motion, research PnP or projected compensation. The available real recording uses an identity-only UNKNOWN calibration, so real camera-motion/residual metrics are unavailable. Analytical tests use explicit synthetic valid geometry. Supply measured calibration before interpreting real camera-motion evidence.
