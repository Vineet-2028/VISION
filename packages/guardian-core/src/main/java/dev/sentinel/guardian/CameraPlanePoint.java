package dev.sentinel.guardian;

import java.util.Objects;

/** Dimensionless optical-plane coordinates X/Z,Y/Z; not bounded to [0,1]. */
public final class CameraPlanePoint {
  private final FrameId frame;
  private final double x;
  private final double y;

  public CameraPlanePoint(FrameId frame, double x, double y) {
    this.frame = Objects.requireNonNull(frame, "frame");
    if (frame.kind() != FrameKind.CAMERA)
      throw new IllegalArgumentException("Expected CAMERA frame");
    this.x = NumericPolicy.finite(x);
    this.y = NumericPolicy.finite(y);
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
