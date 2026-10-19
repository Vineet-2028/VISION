# Image-space motion model

IMPLEMENTED state: center x/y, width/height and their four pixel-per-second rates.
No state represents meters, world motion, ego-motion or collision probability.
Every transition uses actual observation-time dt. Prediction never continues past
the configured observation timeout; invalid/non-finite or non-positive sizes cause
explicit retirement instead of silent clamping.

Alpha-beta baseline uses residual position smoothing and an observation-to-observation
velocity estimate, so extra prediction ticks do not change the velocity dt. A bounded
uncertainty proxy grows during prediction and resets measurement-axis variance after
an observation. This is not statistically calibrated covariance.

Kalman baseline uses four independent 2×2 position/velocity covariance blocks. Each
block uses F=[[1,dt],[0,1]] and acceleration noise Q=q[[dt⁴/4,dt³/2],[dt³/2,dt²]].
Measurement noise R and q are explicit configuration. Joseph-form correction maintains
positive semidefinite covariance. Width/height are linear positive extents; an invalid
prediction retires the track. Fixed dimensions avoid a generic matrix framework.

Both estimators are compared on identical synthetic trajectories. Synthetic covariance
checks do not establish physical uncertainty or superiority on moving-camera footage.
