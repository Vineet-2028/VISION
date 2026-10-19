package dev.sentinel.guardian;

import java.util.Objects;

/**
 * Raw detector/transform box: finite outside-image and zero-area boxes allowed; no automatic clamp.
 */
public final class PixelBox {
  private final FrameId frame;
  private final double minU;
  private final double minV;
  private final double maxU;
  private final double maxV;

  public PixelBox(FrameId frame, double minU, double minV, double maxU, double maxV) {
    this.frame = Objects.requireNonNull(frame, "frame");
    if (frame.kind() != FrameKind.IMAGE) throw new IllegalArgumentException("Expected IMAGE frame");
    this.minU = NumericPolicy.finite(minU);
    this.minV = NumericPolicy.finite(minV);
    this.maxU = NumericPolicy.finite(maxU);
    this.maxV = NumericPolicy.finite(maxV);
    NumericPolicy.nonNegative(maxU - minU);
    NumericPolicy.nonNegative(maxV - minV);
  }

  public double width() {
    return maxU - minU;
  }

  public double height() {
    return maxV - minV;
  }

  public PixelPoint center() {
    return new PixelPoint(frame, minU + width() / 2, minV + height() / 2);
  }

  public PixelPoint bottomCenter() {
    return new PixelPoint(frame, minU + width() / 2, maxV);
  }

  public PixelPoint topLeft() {
    return new PixelPoint(frame, minU, minV);
  }

  public PixelPoint topRight() {
    return new PixelPoint(frame, maxU, minV);
  }

  public PixelPoint bottomLeft() {
    return new PixelPoint(frame, minU, maxV);
  }

  public PixelPoint bottomRight() {
    return new PixelPoint(frame, maxU, maxV);
  }

  public PixelBox clamp(ImageSize image) {
    frame.requireSame(image.frame());
    return new PixelBox(
        frame,
        clampValue(minU, image.width()),
        clampValue(minV, image.height()),
        clampValue(maxU, image.width()),
        clampValue(maxV, image.height()));
  }

  private static double clampValue(double x, double upper) {
    return StrictMath.max(0, StrictMath.min(upper, x));
  }

  public static PixelBox fromNormalized(BoundingBox2D box, ImageSize image) {
    return new PixelBox(
        image.frame(),
        box.minX() * image.width(),
        box.minY() * image.height(),
        box.maxX() * image.width(),
        box.maxY() * image.height());
  }

  public BoundingBox2D toNormalized(ImageSize image) {
    frame.requireSame(image.frame());
    return new BoundingBox2D(
        minU / image.width(), minV / image.height(), maxU / image.width(), maxV / image.height());
  }

  public FrameId frame() {
    return frame;
  }

  public double minU() {
    return minU;
  }

  public double minV() {
    return minV;
  }

  public double maxU() {
    return maxU;
  }

  public double maxV() {
    return maxV;
  }
}
