# Domains and units

IMPLEMENTED: IMAGE_SPACE uses original camera pixels, bbox bottom center and pixel/second rates. CAMERA_BEARING_SPACE uses Guardian-derived azimuth/elevation radians and radian/second rates; angular discontinuities reset the fit. These are camera-relative, never lateral m/s. Camera motion remains an explicit limitation.

LOCAL_WORLD_RESEARCH uses exact timestamp-bound metric-depth/pose joins in a common local frame. Relative depth, unknown calibration, missing/stale pose, wrong calibration or absent source evidence cannot produce this output. Guardian MotionPrediction performs nominal metric extrapolation. x-right/y-forward/z-up conventions are retained; the regression does not swap axes. Every metric result is WORLD_RESEARCH_UNVALIDATED and its velocity RESEARCH_METRIC_ESTIMATE. PHYSICAL_METRIC_VALIDATED is defined for compatibility but never emitted.

Residual motion is an alternate IMAGE_SPACE hypothesis in a named stabilized-research frame. Future camera motion is unknown; it is not overlaid or intersected as raw future-image geometry. No silent conversion of these coordinates occurs.
