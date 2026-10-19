package dev.sentinel.guardian;

import java.util.Optional;
import java.util.OptionalDouble;

/** Single-owner backward derivative in a fixed WORLD frame. No state crosses an explicit reset. */
public final class DerivativeEstimator {
  public enum Status {
    INITIALIZED,
    UPDATED,
    TOO_SOON,
    OUTLIER,
    GAP_RESET,
    UNKNOWN_RESET
  }

  public static final class Result {
    private final Status status;
    private final Optional<TimedVectorEstimate> estimate;
    private final MonotonicTime availableAt;

    private Result(
        Status status, Optional<TimedVectorEstimate> estimate, MonotonicTime availableAt) {
      this.status = status;
      this.estimate = estimate;
      this.availableAt = availableAt;
    }

    public Status status() {
      return status;
    }

    public Optional<TimedVectorEstimate> estimate() {
      return estimate;
    }

    public MonotonicTime availableAt() {
      return availableAt;
    }
  }

  private final VectorEstimate.Quantity inputQuantity, outputQuantity;
  private final long minDtNanos, maxGapNanos;
  private final double maxDerivativeMagnitude;
  private final LowPassFilter filter;
  private TimedVectorEstimate previous;

  public DerivativeEstimator(
      VectorEstimate.Quantity inputQuantity,
      long minDtNanos,
      long maxGapNanos,
      double maxDerivativeMagnitude,
      OptionalDouble cutoffHz) {
    if (inputQuantity != VectorEstimate.Quantity.POSITION_METERS
        && inputQuantity != VectorEstimate.Quantity.VELOCITY_MPS)
      throw new IllegalArgumentException("Derivative requires position or velocity");
    if (minDtNanos < NumericPolicy.MIN_DELTA_NANOS || maxGapNanos < minDtNanos)
      throw new IllegalArgumentException("Invalid derivative interval policy");
    this.inputQuantity = inputQuantity;
    this.outputQuantity =
        inputQuantity == VectorEstimate.Quantity.POSITION_METERS
            ? VectorEstimate.Quantity.VELOCITY_MPS
            : VectorEstimate.Quantity.ACCELERATION_MPS2;
    this.minDtNanos = minDtNanos;
    this.maxGapNanos = maxGapNanos;
    this.maxDerivativeMagnitude = NumericPolicy.nonNegative(maxDerivativeMagnitude);
    filter = cutoffHz.isPresent() ? new LowPassFilter(cutoffHz.getAsDouble(), maxGapNanos) : null;
  }

  private Result result(Status status, MonotonicTime at) {
    return new Result(status, Optional.empty(), at);
  }

  public Result update(TimedVectorEstimate sample) {
    VectorEstimate input = sample.estimate();
    if (input.quantity() != inputQuantity || input.frame().kind() != FrameKind.LOCAL_WORLD)
      throw new IllegalArgumentException("Wrong derivative units/fixed frame");
    if (previous != null) {
      previous.estimate().frame().requireSame(input.frame());
      sample.time().elapsedNanosSince(previous.time());
    }
    if (!input.value().isPresent() || input.confidence().value() == 0) {
      reset();
      return result(Status.UNKNOWN_RESET, sample.time());
    }
    if (previous == null) {
      previous = sample;
      return result(Status.INITIALIZED, sample.time());
    }
    long dt = sample.time().elapsedNanosSince(previous.time());
    if (dt < minDtNanos) return result(Status.TOO_SOON, sample.time());
    if (dt > maxGapNanos) {
      reset();
      previous = sample;
      return result(Status.GAP_RESET, sample.time());
    }
    Vector3 raw =
        input
            .value()
            .get()
            .subtract(previous.estimate().value().get())
            .divide(dt / 1_000_000_000.0);
    if (!OutlierGate.accepts(new Vector3(raw.frame(), 0, 0, 0), raw, maxDerivativeMagnitude))
      return result(Status.OUTLIER, sample.time());
    MonotonicTime midpoint = Temporal.midpoint(previous.time(), sample.time());
    Vector3 output = raw;
    if (filter != null) {
      Optional<Vector3> smoothed = filter.update(raw, midpoint);
      if (!smoothed.isPresent()) {
        previous = sample;
        return result(Status.GAP_RESET, sample.time());
      }
      output = smoothed.get();
    }
    TimedVectorEstimate estimate =
        new TimedVectorEstimate(
            midpoint,
            new VectorEstimate(
                input.frame(),
                outputQuantity,
                Optional.of(output),
                Optional.empty(),
                new Confidence(
                    StrictMath.min(
                        input.confidence().value(), previous.estimate().confidence().value()))));
    previous = sample;
    return new Result(Status.UPDATED, Optional.of(estimate), sample.time());
  }

  public void reset() {
    previous = null;
    if (filter != null) filter.reset();
  }
}
