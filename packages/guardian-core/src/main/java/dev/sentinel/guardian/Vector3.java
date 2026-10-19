package dev.sentinel.guardian;

import java.util.Objects;

/** Immutable components in one frame; quantities/units are defined by the calling contract. */
public final class Vector3 {
  private final FrameId frame;
  private final double x;
  private final double y;
  private final double z;

  public Vector3(FrameId frame, double x, double y, double z) {
    this.frame = Objects.requireNonNull(frame, "frame");
    frame.requireSpatial();
    this.x = NumericPolicy.finite(x);
    this.y = NumericPolicy.finite(y);
    this.z = NumericPolicy.finite(z);
  }

  public Vector3 add(Vector3 other) {
    frame.requireSame(other.frame());
    return new Vector3(frame, x + other.x(), y + other.y(), z + other.z());
  }

  public Vector3 subtract(Vector3 other) {
    frame.requireSame(other.frame());
    return new Vector3(frame, x - other.x(), y - other.y(), z - other.z());
  }

  public Vector3 multiply(double scalar) {
    NumericPolicy.finite(scalar);
    return new Vector3(frame, x * scalar, y * scalar, z * scalar);
  }

  public Vector3 divide(double scalar) {
    NumericPolicy.divisor(scalar);
    return new Vector3(frame, x / scalar, y / scalar, z / scalar);
  }

  public double dot(Vector3 other) {
    frame.requireSame(other.frame());
    return NumericPolicy.finite(x * other.x() + y * other.y() + z * other.z());
  }

  public Vector3 cross(Vector3 other) {
    frame.requireSame(other.frame());
    return new Vector3(
        frame,
        y * other.z() - z * other.y(),
        z * other.x() - x * other.z(),
        x * other.y() - y * other.x());
  }

  public double squaredMagnitude() {
    return dot(this);
  }

  public double magnitude() {
    return NumericPolicy.finite(StrictMath.hypot(StrictMath.hypot(x, y), z));
  }

  public Vector3 normalized() {
    return divide(magnitude());
  }

  public double distance(Vector3 other) {
    return subtract(other).magnitude();
  }

  public double squaredDistance(Vector3 other) {
    return subtract(other).squaredMagnitude();
  }

  public FrameId frame() {
    return frame;
  }

  public double x() {
    return x;
  }

  public double y() {
    return y;
  }

  public double z() {
    return z;
  }
}
