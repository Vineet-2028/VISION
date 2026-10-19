package dev.sentinel.guardian;

import java.util.Objects;

/** Continuous image edges span [0,width] x [0,height]; sensor membership is half-open. */
public final class ImageSize {
  private final FrameId frame;
  private final int width;
  private final int height;

  public ImageSize(FrameId frame, int width, int height) {
    this.frame = Objects.requireNonNull(frame, "frame");
    if (frame.kind() != FrameKind.IMAGE || width <= 0 || height <= 0)
      throw new IllegalArgumentException("Invalid image dimensions/frame");
    this.width = width;
    this.height = height;
  }

  public void requireSame(ImageSize other) {
    frame.requireSame(other.frame);
    if (width != other.width || height != other.height)
      throw new IllegalArgumentException("Image dimensions mismatch");
  }

  public boolean contains(PixelPoint p) {
    frame.requireSame(p.frame());
    return p.u() >= 0 && p.v() >= 0 && p.u() < width && p.v() < height;
  }

  public FrameId frame() {
    return frame;
  }

  public int width() {
    return width;
  }

  public int height() {
    return height;
  }
}
