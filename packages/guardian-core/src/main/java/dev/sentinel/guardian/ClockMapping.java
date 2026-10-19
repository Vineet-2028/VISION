package dev.sentinel.guardian;

import java.util.Optional;

/** Explicit constant offset only. Mapping does not assert measured synchronization accuracy. */
public final class ClockMapping {
  private final String source, target;
  private final long offsetNanos;

  public ClockMapping(String source, String target, long offsetNanos) {
    this.source = NumericPolicy.identity(source);
    this.target = NumericPolicy.identity(target);
    if (source.equals(target)) throw new IllegalArgumentException("Distinct clocks required");
    this.offsetNanos = offsetNanos;
  }

  public Optional<MonotonicTime> map(MonotonicTime time) {
    if (!source.equals(time.clockId())) throw new IllegalArgumentException("Wrong source clock");
    try {
      long mapped = Math.addExact(time.nanos(), offsetNanos);
      return mapped < 0 ? Optional.empty() : Optional.of(new MonotonicTime(target, mapped));
    } catch (ArithmeticException overflow) {
      return Optional.empty();
    }
  }

  public String sourceClock() {
    return source;
  }

  public String targetClock() {
    return target;
  }

  public long offsetNanos() {
    return offsetNanos;
  }
}
