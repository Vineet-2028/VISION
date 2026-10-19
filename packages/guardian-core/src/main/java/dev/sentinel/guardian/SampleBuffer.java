package dev.sentinel.guardian;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

/** Bounded sorted buffer. Single-owner, NOT thread-safe; observations must be immutable. */
public final class SampleBuffer<T extends TimedObservation> {
  public enum Insertion {
    ACCEPTED,
    ACCEPT_AND_REORDER,
    DUPLICATE,
    REJECT_TOO_LATE,
    OUTSIDE_BUFFER
  }

  private final int capacity;
  private final long retentionNanos, lateWindowNanos;
  private final ArrayList<T> samples = new ArrayList<>();
  private String clock;

  public SampleBuffer(int capacity, long retentionNanos, long lateWindowNanos) {
    if (capacity < 1 || retentionNanos < 0 || lateWindowNanos < 0)
      throw new IllegalArgumentException("Invalid buffer policy");
    this.capacity = capacity;
    this.retentionNanos = retentionNanos;
    this.lateWindowNanos = lateWindowNanos;
  }

  private void check(MonotonicTime time) {
    Objects.requireNonNull(time, "time");
    if (clock != null && !clock.equals(time.clockId()))
      throw new IllegalArgumentException("Reset before clock change");
  }

  private int lowerBound(MonotonicTime time) {
    check(time);
    int lo = 0, hi = samples.size();
    while (lo < hi) {
      int mid = lo + (hi - lo) / 2;
      if (samples.get(mid).time().nanos() < time.nanos()) lo = mid + 1;
      else hi = mid;
    }
    return lo;
  }

  public Insertion add(T sample) {
    Objects.requireNonNull(sample, "sample");
    MonotonicTime t = sample.time();
    int index = lowerBound(t);
    if (index < samples.size() && samples.get(index).time().equals(t)) return Insertion.DUPLICATE;
    boolean late = !samples.isEmpty() && t.nanos() < samples.get(samples.size() - 1).time().nanos();
    if (late) {
      long age = samples.get(samples.size() - 1).time().nanos() - t.nanos();
      if (age > retentionNanos || (samples.size() == capacity && index == 0))
        return Insertion.OUTSIDE_BUFFER;
      if (age > lateWindowNanos) return Insertion.REJECT_TOO_LATE;
    }
    samples.add(index, sample);
    clock = t.clockId();
    long newest = samples.get(samples.size() - 1).time().nanos();
    int evict = 0;
    while (evict < samples.size()
        && (samples.size() - evict > capacity
            || newest - samples.get(evict).time().nanos() > retentionNanos)) evict++;
    if (evict > 0) samples.subList(0, evict).clear();
    return late ? Insertion.ACCEPT_AND_REORDER : Insertion.ACCEPTED;
  }

  public Optional<T> atOrBefore(MonotonicTime time) {
    int i = lowerBound(time);
    if (i < samples.size() && samples.get(i).time().equals(time))
      return Optional.of(samples.get(i));
    return i == 0 ? Optional.empty() : Optional.of(samples.get(i - 1));
  }

  public Optional<T> atOrAfter(MonotonicTime time) {
    int i = lowerBound(time);
    return i == samples.size() ? Optional.empty() : Optional.of(samples.get(i));
  }

  public Optional<T> nearest(MonotonicTime time) {
    Optional<T> a = atOrBefore(time), b = atOrAfter(time);
    if (!a.isPresent()) return b;
    if (!b.isPresent()) return a;
    return Temporal.distanceNanos(a.get().time(), time)
            <= Temporal.distanceNanos(b.get().time(), time)
        ? a
        : b;
  }

  public List<T> snapshot() {
    return Collections.unmodifiableList(new ArrayList<>(samples));
  }

  public int size() {
    return samples.size();
  }

  public void reset() {
    samples.clear();
    clock = null;
  }
}
