package dev.sentinel.guardian;

import java.util.Objects;

/** Continuous pixel-edge coordinates; off-image finite points are allowed. */
public final class PixelPoint {
  private final FrameId frame;
  private final double u;
  private final double v;

  public PixelPoint(FrameId frame, double u, double v) {
    this.frame = Objects.requireNonNull(frame, "frame");
    if (frame.kind() != FrameKind.IMAGE) throw new IllegalArgumentException("Expected IMAGE frame");
    this.u = NumericPolicy.finite(u);
    this.v = NumericPolicy.finite(v);
  }

  public FrameId frame() {
    return frame;
  }

  public double u() {
    return u;
  }

  public double v() {
    return v;
  }
}
