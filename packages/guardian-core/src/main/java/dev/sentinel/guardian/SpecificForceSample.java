package dev.sentinel.guardian;

import java.util.Objects;

/** DEVICE specific force f=a-g, m/s^2, at measurement time. */
public final class SpecificForceSample implements TimedObservation {
  private final MonotonicTime time;
  private final Vector3 value;

  public SpecificForceSample(MonotonicTime time, Vector3 value) {
    if (value.frame().kind() != FrameKind.DEVICE)
      throw new IllegalArgumentException("DEVICE specific force required");
    this.time = Objects.requireNonNull(time, "time");
    this.value = value;
  }

  public MonotonicTime time() {
    return time;
  }

  public Vector3 metersPerSecondSquared() {
    return value;
  }
}
