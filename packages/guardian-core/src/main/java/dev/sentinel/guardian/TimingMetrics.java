package dev.sentinel.guardian;

/** Single-owner interval statistics; no fixed-rate assumption and no system clock. */
public final class TimingMetrics {
  public static final class Gap {
    private final long observedNanos, expectedNanos;
    private final double ratio;
    private final boolean exceeds;

    private Gap(long observed, long expected, double limit) {
      observedNanos = observed;
      expectedNanos = expected;
      ratio = (double) observed / expected;
      exceeds = ratio > limit;
    }

    public long observedNanos() {
      return observedNanos;
    }

    public long expectedNanos() {
      return expectedNanos;
    }

    public double ratio() {
      return ratio;
    }

    public boolean exceedsConfiguredRatio() {
      return exceeds;
    }
  }

  private final Statistics intervals = new Statistics();
  private MonotonicTime previous;

  public void add(MonotonicTime time) {
    if (previous != null) {
      long gap = time.elapsedNanosSince(previous);
      if (gap == 0) throw new IllegalArgumentException("Positive intervals required");
      intervals.add(gap / 1_000_000_000.0);
    }
    previous = time;
  }

  public static Gap gap(
      MonotonicTime earlier, MonotonicTime later, long expectedPeriodNanos, double maxRatio) {
    if (expectedPeriodNanos <= 0 || NumericPolicy.finite(maxRatio) < 1)
      throw new IllegalArgumentException("Invalid gap policy");
    return new Gap(later.elapsedNanosSince(earlier), expectedPeriodNanos, maxRatio);
  }

  public long intervalCount() {
    return intervals.count();
  }

  public double meanSeconds() {
    return intervals.mean();
  }

  public double standardDeviationSeconds() {
    return intervals.standardDeviation();
  }

  public double minSeconds() {
    return intervals.min();
  }

  public double maxSeconds() {
    return intervals.max();
  }

  public void reset() {
    previous = null;
    intervals.reset();
  }
}
