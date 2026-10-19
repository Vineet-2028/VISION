# Motion decomposition

OBSERVED_IMAGE_MOTION = CAMERA_INDUCED_IMAGE_MOTION + INDEPENDENT_SCENE_MOTION + MEASUREMENT_ERROR.

IMPLEMENTED: residual = observed displacement minus projected camera-induced displacement, in original calibrated image pixels per ordered frame pair. ROTATION_ONLY leaves translation-induced parallax. DEPTH_SCALED_RESEARCH_UNVALIDATED_SCALE includes explicitly supplied frame-A metric-model depth and research translation. Unscaled translation direction is never applied as a metric displacement.

Residual is camera-compensated image motion, not an independent-motion guarantee or physical velocity. Pixels/second uses integer observation-time subtraction followed by conversion to seconds. No meters/second, TTC, CPA, collision, navigation or hazard decisions are emitted.

TrackImageMotionObservation samples endpoint-B points inside an eroded latest observed box, using component medians and MAD. Predicted-only or stale tracks receive no fresh summary. Empty/insufficient samples remain unavailable. Track identity is inherited prototype identity, not re-identification. Track depth can be joined later using exact source/session/frame identities; no automatic depth-times-flow physical-speed formula exists.

UNVALIDATED: background/foreground separability without independent static/dynamic labels. A stationary object can retain residual due to camera translation, rolling shutter, calibration error or correspondence error. A coherently moving foreground majority can masquerade as camera motion; robust estimation cannot resolve this observability ambiguity alone.
