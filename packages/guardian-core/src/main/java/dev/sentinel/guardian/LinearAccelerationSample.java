package dev.sentinel.guardian;

import java.util.Objects;

/** Gravity-compensated linear acceleration; gravity is excluded. */
public final class LinearAccelerationSample implements TimedObservation {
  private final MonotonicTime time;
  private final Vector3 metersPerSecondSquared;

  public LinearAccelerationSample(MonotonicTime time, Vector3 metersPerSecondSquared) {
    this.time = Objects.requireNonNull(time, "time");
    this.metersPerSecondSquared =
        Objects.requireNonNull(metersPerSecondSquared, "metersPerSecondSquared");
  }

  public MonotonicTime time() {
    return time;
  }

  public Vector3 metersPerSecondSquared() {
    return metersPerSecondSquared;
  }
}
