package dev.sentinel.guardian;

import java.util.Optional;
import java.util.function.Predicate;

/** Single-owner lookup over a buffer. Invalid observations are barriers, never skipped. */
final class TemporalLookup {
  interface Interpolator<T> {
    Optional<T> at(T a, T b, MonotonicTime query);
  }

  private TemporalLookup() {}

  static <T extends TimedObservation> TemporalAlignment<T> lookup(
      SampleBuffer<T> buffer,
      MonotonicTime query,
      SynchronizationPolicy policy,
      Predicate<T> valid,
      Interpolator<T> interpolate) {
    Optional<T> a = buffer.atOrBefore(query), b = buffer.atOrAfter(query);
    if (a.isPresent() && a.get().time().equals(query)) {
      if (!valid.test(a.get())) return TemporalAlignment.unavailable(query);
      return new TemporalAlignment<>(TemporalAlignment.Mode.EXACT, query, a, a, a);
    }
    if (a.isPresent() && b.isPresent()) {
      if (!valid.test(a.get()) || !valid.test(b.get())) return TemporalAlignment.unavailable(query);
      if (b.get().time().elapsedNanosSince(a.get().time()) <= policy.maxSpanNanos()) {
        Optional<T> value = interpolate.at(a.get(), b.get(), query);
        if (value.isPresent())
          return new TemporalAlignment<>(TemporalAlignment.Mode.INTERPOLATED, query, value, a, b);
        return TemporalAlignment.unavailable(query);
      }
    }
    if (policy.nearestAllowed()) {
      Optional<T> nearest = policy.futureNearestAllowed() ? buffer.nearest(query) : a;
      if (nearest.isPresent()
          && valid.test(nearest.get())
          && Temporal.distanceNanos(query, nearest.get().time()) <= policy.maxNearestAgeNanos())
        return new TemporalAlignment<>(
            TemporalAlignment.Mode.NEAREST_ALLOWED, query, nearest, nearest, nearest);
    }
    return TemporalAlignment.unavailable(query);
  }
}
