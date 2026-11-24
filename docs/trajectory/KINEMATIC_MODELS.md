# Kinematic models

IMPLEMENTED: constant position, CV-last-two comparison, CV-window and adaptive selection. Authoritative nanosecond differences determine seconds; no fixed frame interval. Default horizons:0.25,0.5,1,1.5,2,3 seconds. No prediction beyond3 seconds.

Primary candidate: adaptive bounded robust window fit. A median of temporally separated pair slopes seeds inlier rejection, followed by least-squares on retained observations. This replaces the initial expensive all-pairs seed. At most32 samples; no entity interactions. This is a robust heuristic, not a guarantee against adversarial majority corruption.

Default CV needs at least3 observations over100ms, no retained gap above500ms, and residual <=4 times the domain floor. Otherwise CP is used. Displacement <=domain floor selects the stationary hypothesis. Outlier rejection degrades quality. Single-observation identity resets do not borrow another track's history. Predicted-only tracker samples are excluded entirely.

CP is a real stationary/fallback hypothesis; with stable history its position may be denoised by the fit. CV-last-two is retained for experiments, not selected as default. CA is explicitly DEFERRED: short, noisy, fragmented histories do not justify an additional derivative. Acceleration synthetic cases expose CV limits rather than implying CA accuracy.
