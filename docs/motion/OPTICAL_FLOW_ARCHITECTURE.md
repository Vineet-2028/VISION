# Optical flow architecture

IMPLEMENTED: optional Task009 CPU flow in the local Python lab. FlowAdapter owns exactly one previous grayscale image; ClassicalFlowProvider selects pyramidal LK or DIS. No neural weights, CUDA, detector or depth are required. OpenCV imports stay in runtime adapters. The web/API and Java core do not depend on optical flow.

Frame A/B -> FlowObservation -> bounded sparse correspondences -> EgoMotionEstimator -> CameraMotionEstimate -> ResidualFlow -> observed-track summaries. Dense DIS stays at processed resolution. Dense sampling is a uniform bounded grid. Arrays have immutable owned storage; no flow history or per-track inference. Session teardown releases the previous image.

PROVISIONAL: LK at maximum side 640, 400 features, forward/backward threshold 1.5 processed pixels, 100-200 RANSAC iterations. Configuration is versioned and exported with its hash. Actual source timestamps control pairing and cadence. Unsupported gaps reset the adapter; they are never treated as normal motion.

Recording schema4 stores pair/provenance/quality and compact camera/track results. Dense arrays are excluded before serialization. Debug flow recording is currently unsupported; no private images are exported by default. Metadata logs remain opt-in and need external disk retention for long sessions.

PLANNED: a mobile provider can return these same Sentinel contracts; learned flow is optional future research. Task010 segmentation can implement SemanticExclusion without changing estimators. No Task010 implementation is included.
