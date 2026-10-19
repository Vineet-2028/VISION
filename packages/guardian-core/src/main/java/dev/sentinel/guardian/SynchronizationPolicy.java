package dev.sentinel.guardian;

/** Consumer-provided limits; nearest is opt-in and never relabeled as exact. */
public final class SynchronizationPolicy {
  private final long maxSpanNanos, maxNearestAgeNanos;
  private final boolean nearestAllowed, futureNearestAllowed;

  public SynchronizationPolicy(
      long maxSpanNanos,
      long maxNearestAgeNanos,
      boolean nearestAllowed,
      boolean futureNearestAllowed) {
    if (maxSpanNanos < 0 || maxNearestAgeNanos < 0)
      throw new IllegalArgumentException("Negative synchronization limit");
    this.maxSpanNanos = maxSpanNanos;
    this.maxNearestAgeNanos = maxNearestAgeNanos;
    this.nearestAllowed = nearestAllowed;
    this.futureNearestAllowed = futureNearestAllowed;
  }

  public long maxSpanNanos() {
    return maxSpanNanos;
  }

  public long maxNearestAgeNanos() {
    return maxNearestAgeNanos;
  }

  public boolean nearestAllowed() {
    return nearestAllowed;
  }

  public boolean futureNearestAllowed() {
    return futureNearestAllowed;
  }
}
