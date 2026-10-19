package dev.sentinel.guardian;

import java.util.Objects;

/** Timestamped SI vector estimate; validity/uncertainty live in the existing estimate. */
public final class TimedVectorEstimate implements TimedObservation {
  private final MonotonicTime time;
  private final VectorEstimate estimate;

  public TimedVectorEstimate(MonotonicTime time, VectorEstimate estimate) {
    this.time = Objects.requireNonNull(time, "time");
    this.estimate = Objects.requireNonNull(estimate, "estimate");
  }

  public MonotonicTime time() {
    return time;
  }

  public VectorEstimate estimate() {
    return estimate;
  }
}
