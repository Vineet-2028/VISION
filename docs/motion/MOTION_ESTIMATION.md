# Streaming derivatives and prediction

## IMPLEMENTED

DerivativeEstimator has explicit POSITION_METERS->VELOCITY_MPS or
VELOCITY_MPS->ACCELERATION_MPS2 configuration. It shares one implementation rather
than duplicating nearly identical state machines. Only fixed LOCAL_WORLD input is
accepted: rotating DEVICE coordinates cannot be differentiated as world motion.

Backward difference is (new-old)/actual_dt. Output time is the interval midpoint
(start+(end-start)/2); availableAt records the later measurement time. This is an
interval-average derivative, not an instantaneous endpoint estimate. Optional
low-pass smoothing adds lag; the midpoint label does not eliminate filter delay.

The first input yields INITIALIZED without an estimate. Inputs below the configured
minimum interval yield TOO_SOON and do not advance the baseline. The minimum cannot
be less than Task 002's 1000 ns mathematical differentiation guard. Unknown or
zero-confidence input clears state; excessive gaps reset and reinitialize. Outliers
do not update baseline or filter. Mismatched frames/clocks throw, requiring an
explicit reset before a new session. No stale derivative is returned on rejection.

Outlier acceptance uses a consumer-supplied maximum derivative magnitude. No universal
human speed/acceleration limit is embedded. Statistical innovation gating with modeled
covariance is future work. Filtered acceleration remains sensitive to noise and lag.

MotionPrediction explicitly selects CONSTANT_POSITION, CONSTANT_VELOCITY or
CONSTANT_ACCELERATION:

    CP: p_next = p
    CV: p_next = p + v*dt
    CA: p_next = p + v*dt + 0.5*a*dt²
        v_next = v + a*dt

Inputs must share WORLD frame, units and observation time; target must not precede
them. The caller supplies a maximum horizon. No model is chosen automatically.

Derived deviations are unknown; confidence never increases above the least-confident
contributing input. Sources must be retained by the caller. Prediction horizon
does not imply an accuracy bound.

## PLANNED / RESEARCH

For independent position errors, velocity variance includes (var(p0)+var(p1))/dt²;
correlated errors require cross terms. Second differentiation amplifies noise further.
Interpolation needs temporal/model uncertainty in addition to endpoint uncertainty.
Prediction needs process noise growing with horizon. Full covariance requires measured
noise and correlation models, not fabricated matrices.

Central differences require a future sample and add latency; for irregular sampling,
the simple two-endpoint difference is an interval average, not generally the derivative
at the interior timestamp. Only streaming backward differences are implemented.
CV versus CA selection, Kalman/alpha-beta and validated covariance remain research.
