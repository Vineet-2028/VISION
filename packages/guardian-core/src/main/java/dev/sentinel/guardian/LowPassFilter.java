package dev.sentinel.guardian;

import java.util.Optional;

/** Single-owner adaptive Vector3 low-pass. Rejected inputs never mutate state. */
public final class LowPassFilter {
  private final double cutoffHz;
  private final long maxGapNanos;
  private Vector3 value;
  private MonotonicTime time;

  public LowPassFilter(double cutoffHz, long maxGapNanos) {
    if (NumericPolicy.finite(cutoffHz) <= 0 || maxGapNanos < 1)
      throw new IllegalArgumentException("Invalid filter policy");
    this.cutoffHz = cutoffHz;
    this.maxGapNanos = maxGapNanos;
  }

  public Optional<Vector3> update(Vector3 input, MonotonicTime at) {
    java.util.Objects.requireNonNull(input, "input");
    java.util.Objects.requireNonNull(at, "time");
    if (value == null) {
      value = input;
      time = at;
      return Optional.of(input);
    }
    value.frame().requireSame(input.frame());
    long nanos = at.elapsedNanosSince(time);
    if (nanos == 0) throw new IllegalArgumentException("Positive filter dt required");
    if (nanos > maxGapNanos) {
      reset();
      value = input;
      time = at;
      return Optional.empty();
    }
    double dt = nanos / 1_000_000_000.0;
    // Divide sequentially to avoid overflow in 2*pi*fc or tau+dt.
    double tau = 1 / cutoffHz / (2 * StrictMath.PI);
    double alpha = 1 / (1 + tau / dt);
    Vector3 next = Interpolation.vector(value, input, alpha);
    value = next;
    time = at;
    return Optional.of(next);
  }

  public void reset() {
    value = null;
    time = null;
  }
}
