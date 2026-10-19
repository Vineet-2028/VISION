# Metric depth and geometry

IMPLEMENTED analytical geometry; physical ranging remains UNVALIDATED.

For a calibrated unit ray r and camera optical-axis depth Z, point = r * (Z/r.z). For Euclidean ray range d, point = r*d. These differ off-axis. Guardian supplies the ray and performs vector scaling. Tests exercise both interpretations.

A robust ROI statistic projected at its representative center is a hypothesis about a visible surface, not an exact measured object center. CameraPointEstimate preserves its source estimate, frame, calibration quality and UNKNOWN uncertainty. Synthetic/UNKNOWN calibration does not become physically validated because the algebra passes.

The typed SuppliedDepthPose and WorldPointEstimate boundary preserves frame identity and rejects a different device frame. World projection requires explicitly matching frame/source/time identity and camera-to-device extrinsics. Guardian DevicePoseEstimate and RigidTransform perform CAMERA -> DEVICE -> LOCAL_WORLD composition. Missing extrinsics return unavailable; mismatched identity is rejected. No latest-pose substitution or pose estimation occurs.

Depth Anything outdoor research output is interpreted as camera Z following upstream point-cloud construction. It does not consume measured intrinsics for inference. Its configured 80 m range is a model support limit, not a demonstrated accuracy range on Sentinel footage.

Ground-plane cross-checks require real calibration, matching pose, an appropriate plane and a valid object contact point. Current user footage has placeholder calibration, so no real ground-consistency accuracy is claimed. Do not fuse plane and model depth without error characterization.

Future point uncertainty must include pixel localization, depth, calibration and pose uncertainty; region MAD is not metric standard deviation. Later physical motion requires camera-motion compensation. Depth differences alone must not feed TTC/CPA.

Optional future micro-benchmark: record a static camera with measured surfaces at 1, 2, 3 and 5 m, document whether measurements are optical Z or range, calibration and measurement uncertainty, and compare repeated estimates without fitting on the held-out samples.
