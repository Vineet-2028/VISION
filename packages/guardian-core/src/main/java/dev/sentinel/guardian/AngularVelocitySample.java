package dev.sentinel.guardian;

import java.util.Objects;

/** Right-handed angular velocity in radians/second. */
public final class AngularVelocitySample implements TimedObservation {
  private final MonotonicTime time;
  private final Vector3 radiansPerSecond;

  public AngularVelocitySample(MonotonicTime time, Vector3 radiansPerSecond) {
    this.time = Objects.requireNonNull(time, "time");
    this.radiansPerSecond = Objects.requireNonNull(radiansPerSecond, "radiansPerSecond");
  }

  public MonotonicTime time() {
    return time;
  }

  public Vector3 radiansPerSecond() {
    return radiansPerSecond;
  }
}
