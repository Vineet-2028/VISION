package dev.sentinel.guardian;

/** Clock-explicit arithmetic. No clock reads or device timing thresholds. */
public final class Temporal {
  public enum Age {
    FRESH,
    STALE,
    FUTURE,
    INVALID
  }

  private Temporal() {}

  public static double durationSeconds(MonotonicTime start, MonotonicTime end) {
    return end.elapsedNanosSince(start) / 1_000_000_000.0;
  }

  public static long distanceNanos(MonotonicTime a, MonotonicTime b) {
    a.requireSameClock(b);
    return a.nanos() >= b.nanos() ? a.nanos() - b.nanos() : b.nanos() - a.nanos();
  }

  public static Age age(
      MonotonicTime query, MonotonicTime sample, long maxAgeNanos, boolean valid) {
    if (maxAgeNanos < 0) throw new IllegalArgumentException("Negative age limit");
    query.requireSameClock(sample);
    if (!valid) return Age.INVALID;
    if (sample.nanos() > query.nanos()) return Age.FUTURE;
    return query.nanos() - sample.nanos() <= maxAgeNanos ? Age.FRESH : Age.STALE;
  }

  public static MonotonicTime midpoint(MonotonicTime a, MonotonicTime b) {
    return new MonotonicTime(a.clockId(), a.nanos() + b.elapsedNanosSince(a) / 2);
  }
}
