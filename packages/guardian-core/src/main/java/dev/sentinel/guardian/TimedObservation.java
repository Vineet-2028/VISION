package dev.sentinel.guardian;

/** Immutable observation whose time denotes measurement, never delivery. */
public interface TimedObservation {
  MonotonicTime time();
}
