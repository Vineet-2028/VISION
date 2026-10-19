# Filtering and statistics

## IMPLEMENTED

LowPassFilter uses actual elapsed time:

    tau = 1/(2*pi*cutoffHz)
    alpha = dt/(tau+dt)
    output = (1-alpha)*previous + alpha*input

The implementation rearranges alpha to avoid overflowing tau+dt. It supports
Vector3, first-sample initialization, reset and a caller-supplied maximum gap.
Duplicate/backward timestamps and incompatible frames/clocks reject without
updating state. A gap beyond the configured limit clears history, seeds from the
new input, and returns unavailable for that transition. Reset on sensor/session,
calibration or orientation discontinuity is an adapter responsibility.

This is exponential smoothing with adaptive alpha; a second smoothing class would
duplicate it. Weighted interpolation avoids needless overflow from subtracting
opposite large finite values. Finite output or explicit failure is required.

Median3Filter is a tiny causal scalar spike filter: unavailable until three samples,
then median of the latest three. It has no timestamps; the caller owns cadence,
discontinuity resets and labeling. On a monotonic regularly sampled signal it delays
the signal by one sample. It must not silently be treated as zero-latency filtering.

OutlierGate supplies configurable absolute scalar/vector residual limits. It never
chooses sensor thresholds. DerivativeEstimator additionally applies a configured
maximum derivative magnitude before state/filter updates.

Statistics uses Welford updates for count, mean and population variance, with
finite transactional updates and reset. TimingMetrics uses it for interval jitter.
Variance is population variance over the supplied window, not a sensor-noise claim.

Stateful utilities are single-owner, NOT thread-safe. No mutable static state,
background threads, global locks or exposed internal arrays exist.

## PLANNED / RESEARCH

High-pass filtering is deferred: no current consumer requires it.
Scalar/CV Kalman and alpha-beta filters are also deferred to a task with an actual
tracking measurement model and characterized process/measurement noise. Alpha-beta
offers a small fixed-gain CV correction but needs cadence-aware tuning; Kalman
supports modeled uncertainty at greater complexity. Implementing both now would
introduce unsupported tuning and duplicate estimators. No generic matrix package,
complementary orientation filter or full ESKF is introduced.
