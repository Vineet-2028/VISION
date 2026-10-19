package dev.sentinel.guardian;

import java.util.Objects;
import java.util.Optional;

/** Half-line with metric origin, unit direction and optional capture time; no depth measurement. */
public final class Ray3D {
  private final Vector3 origin, direction;
  private final Optional<MonotonicTime> time;

  public Ray3D(Vector3 origin, Vector3 direction, Optional<MonotonicTime> time) {
    origin.frame().requireSame(direction.frame());
    this.origin = origin;
    this.direction = direction.normalized();
    this.time = Objects.requireNonNull(time, "time");
  }

  public Vector3 origin() {
    return origin;
  }

  public Vector3 direction() {
    return direction;
  }

  public FrameId frame() {
    return origin.frame();
  }

  public Optional<MonotonicTime> time() {
    return time;
  }

  public Vector3 pointAt(double distanceMeters) {
    return origin.add(direction.multiply(NumericPolicy.nonNegative(distanceMeters)));
  }
}
