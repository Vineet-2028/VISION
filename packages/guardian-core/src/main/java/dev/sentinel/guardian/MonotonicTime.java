package dev.sentinel.guardian;

/** Elapsed nanoseconds from a session clock origin, never Unix time. */
public final class MonotonicTime implements Comparable<MonotonicTime> {
  private final String clockId;
  private final long nanos;

  public MonotonicTime(String clockId, long nanos) {
    this.clockId = NumericPolicy.identity(clockId);
    if (nanos < 0) throw new IllegalArgumentException("Elapsed sensor time must be nonnegative");
    this.nanos = nanos;
  }

  public void requireSameClock(MonotonicTime other) {
    if (!clockId.equals(other.clockId()))
      throw new IllegalArgumentException("Unsynchronized clocks");
  }

  /** this (later) minus earlier; zero allowed for ordering, not differentiation. */
  public long elapsedNanosSince(MonotonicTime earlier) {
    requireSameClock(earlier);
    if (nanos < earlier.nanos()) throw new IllegalArgumentException("Negative interval");
    return nanos - earlier.nanos();
  }

  public double motionSecondsSince(MonotonicTime earlier) {
    long delta = elapsedNanosSince(earlier);
    if (delta < NumericPolicy.MIN_DELTA_NANOS)
      throw new IllegalArgumentException("Insufficient delta time");
    return delta / 1_000_000_000.0;
  }

  @Override
  public int compareTo(MonotonicTime other) {
    requireSameClock(other);
    return Long.compare(nanos, other.nanos());
  }

  @Override
  public boolean equals(Object other) {
    if (!(other instanceof MonotonicTime)) return false;
    MonotonicTime time = (MonotonicTime) other;
    return clockId.equals(time.clockId()) && nanos == time.nanos();
  }

  @Override
  public int hashCode() {
    return 31 * clockId.hashCode() + Long.hashCode(nanos);
  }

  public String clockId() {
    return clockId;
  }

  public long nanos() {
    return nanos;
  }
}
