package dev.sentinel.guardian;

import java.util.Optional;
import java.util.OptionalLong;

/** Immutable provenance. NEAREST_ALLOWED value retains its actual measurement timestamp. */
public final class TemporalAlignment<T extends TimedObservation> {
  public enum Mode {
    EXACT,
    INTERPOLATED,
    NEAREST_ALLOWED,
    UNAVAILABLE
  }

  private final Mode mode;
  private final MonotonicTime requestedTime;
  private final Optional<T> value, firstSource, lastSource;

  TemporalAlignment(
      Mode mode,
      MonotonicTime requestedTime,
      Optional<T> value,
      Optional<T> first,
      Optional<T> last) {
    this.mode = mode;
    this.requestedTime = requestedTime;
    this.value = value;
    this.firstSource = first;
    this.lastSource = last;
  }

  static <T extends TimedObservation> TemporalAlignment<T> unavailable(MonotonicTime query) {
    return new TemporalAlignment<>(
        Mode.UNAVAILABLE, query, Optional.empty(), Optional.empty(), Optional.empty());
  }

  public Mode mode() {
    return mode;
  }

  public MonotonicTime requestedTime() {
    return requestedTime;
  }

  public Optional<T> value() {
    return value;
  }

  public Optional<T> firstSource() {
    return firstSource;
  }

  public Optional<T> lastSource() {
    return lastSource;
  }

  public long interpolationSpanNanos() {
    return firstSource.isPresent()
        ? lastSource.get().time().elapsedNanosSince(firstSource.get().time())
        : 0;
  }

  /** Signed age relative to requested time: negative means a future source. */
  public OptionalLong firstSourceAgeNanos() {
    return firstSource.isPresent()
        ? OptionalLong.of(requestedTime.nanos() - firstSource.get().time().nanos())
        : OptionalLong.empty();
  }

  public OptionalLong lastSourceAgeNanos() {
    return lastSource.isPresent()
        ? OptionalLong.of(requestedTime.nanos() - lastSource.get().time().nanos())
        : OptionalLong.empty();
  }
}
