package dev.sentinel.guardian;

import java.util.Objects;

/** Immutable components in one frame; quantities/units are defined by the calling contract. */
public final class Vector2 {
  private final FrameId frame;
  private final double x;
  private final double y;

  public Vector2(FrameId frame, double x, double y) {
    this.frame = Objects.requireNonNull(frame, "frame");

    this.x = NumericPolicy.finite(x);
    this.y = NumericPolicy.finite(y);
  }

  public Vector2 add(Vector2 other) {
    frame.requireSame(other.frame());
    return new Vector2(frame, x + other.x(), y + other.y());
  }

  public Vector2 subtract(Vector2 other) {
    frame.requireSame(other.frame());
    return new Vector2(frame, x - other.x(), y - other.y());
  }

  public Vector2 multiply(double scalar) {
    NumericPolicy.finite(scalar);
    return new Vector2(frame, x * scalar, y * scalar);
  }

  public Vector2 divide(double scalar) {
    NumericPolicy.divisor(scalar);
    return new Vector2(frame, x / scalar, y / scalar);
  }

  public double dot(Vector2 other) {
    frame.requireSame(other.frame());
    return NumericPolicy.finite(x * other.x() + y * other.y());
  }

  public double squaredMagnitude() {
    return dot(this);
  }

  public double magnitude() {
    return NumericPolicy.finite(StrictMath.hypot(x, y));
  }

  public Vector2 normalized() {
    return divide(magnitude());
  }

  public double distance(Vector2 other) {
    return subtract(other).magnitude();
  }

  public double squaredDistance(Vector2 other) {
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
}
