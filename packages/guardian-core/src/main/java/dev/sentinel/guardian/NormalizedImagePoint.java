package dev.sentinel.guardian;

import java.util.Objects;

/** Bounded [0,1] image coordinates, NOT normalized optical-plane coordinates. */
public final class NormalizedImagePoint {
  private final FrameId frame;
  private final double x;
  private final double y;

  public NormalizedImagePoint(FrameId frame, double x, double y) {
    this.frame = Objects.requireNonNull(frame, "frame");
    if (frame.kind() != FrameKind.IMAGE
        || NumericPolicy.nonNegative(x) > 1
        || NumericPolicy.nonNegative(y) > 1)
      throw new IllegalArgumentException("Invalid normalized image point");
    this.x = x;
    this.y = y;
  }

  public PixelPoint toPixels(ImageSize image) {
    frame.requireSame(image.frame());
    return new PixelPoint(frame, x * image.width(), y * image.height());
  }

  public static NormalizedImagePoint fromPixels(PixelPoint p, ImageSize image) {
    image.frame().requireSame(p.frame());
    return new NormalizedImagePoint(p.frame(), p.u() / image.width(), p.v() / image.height());
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
