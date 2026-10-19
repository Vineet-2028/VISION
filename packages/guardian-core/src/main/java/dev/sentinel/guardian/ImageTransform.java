package dev.sentinel.guardian;

/**
 * Axis-aligned affine image geometry: scaling, crop, padding and clockwise quarter turns.
 * Coordinates are continuous edges; factories never assume unknown resize/warp behavior.
 */
public final class ImageTransform {
  private final ImageSize from, to;
  private final double a, b, c, d, tx, ty;

  private ImageTransform(
      ImageSize from, ImageSize to, double a, double b, double c, double d, double tx, double ty) {
    this.from = from;
    this.to = to;
    this.a = NumericPolicy.finite(a);
    this.b = NumericPolicy.finite(b);
    this.c = NumericPolicy.finite(c);
    this.d = NumericPolicy.finite(d);
    this.tx = NumericPolicy.finite(tx);
    this.ty = NumericPolicy.finite(ty);
    double det = NumericPolicy.finite(a * d - b * c);
    if (det == 0) throw new IllegalArgumentException("Singular image transform");
  }

  public ImageSize from() {
    return from;
  }

  public ImageSize to() {
    return to;
  }

  public static ImageTransform scale(ImageSize from, ImageSize to) {
    requireDistinctFrames(from.frame(), to.frame());
    return new ImageTransform(
        from,
        to,
        (double) to.width() / from.width(),
        0,
        0,
        (double) to.height() / from.height(),
        0,
        0);
  }

  public static ImageTransform crop(ImageSize from, ImageSize to, int left, int top) {
    requireDistinctFrames(from.frame(), to.frame());
    if (left < 0
        || top < 0
        || (long) left + to.width() > from.width()
        || (long) top + to.height() > from.height())
      throw new IllegalArgumentException("Crop outside source");
    return new ImageTransform(from, to, 1, 0, 0, 1, -left, -top);
  }

  public static ImageTransform pad(ImageSize from, ImageSize to, int left, int top) {
    requireDistinctFrames(from.frame(), to.frame());
    if (left < 0
        || top < 0
        || (long) left + from.width() > to.width()
        || (long) top + from.height() > to.height())
      throw new IllegalArgumentException("Invalid padding");
    return new ImageTransform(from, to, 1, 0, 0, 1, left, top);
  }

  /**
   * Ideal continuous letterboxing with symmetric fractional padding; no hidden integer rounding.
   */
  public static ImageTransform letterbox(ImageSize from, ImageSize to) {
    requireDistinctFrames(from.frame(), to.frame());
    double s =
        StrictMath.min((double) to.width() / from.width(), (double) to.height() / from.height());
    return new ImageTransform(
        from,
        to,
        s,
        0,
        0,
        s,
        (to.width() - s * from.width()) / 2,
        (to.height() - s * from.height()) / 2);
  }

  public static ImageTransform rotateClockwise(ImageSize from, FrameId toFrame, int quarterTurns) {
    requireDistinctFrames(from.frame(), toFrame);
    if (quarterTurns < 0 || quarterTurns > 3)
      throw new IllegalArgumentException("Quarter turns must be 0..3");
    ImageSize to =
        new ImageSize(
            toFrame,
            quarterTurns % 2 == 0 ? from.width() : from.height(),
            quarterTurns % 2 == 0 ? from.height() : from.width());
    switch (quarterTurns) {
      case 0:
        return new ImageTransform(from, to, 1, 0, 0, 1, 0, 0);
      case 1:
        return new ImageTransform(from, to, 0, -1, 1, 0, from.height(), 0);
      case 2:
        return new ImageTransform(from, to, -1, 0, 0, -1, from.width(), from.height());
      default:
        return new ImageTransform(from, to, 0, 1, -1, 0, 0, from.width());
    }
  }

  public PixelPoint forward(PixelPoint p) {
    from.frame().requireSame(p.frame());
    return new PixelPoint(to.frame(), a * p.u() + b * p.v() + tx, c * p.u() + d * p.v() + ty);
  }

  static void requireDistinctFrames(FrameId from, FrameId to) {
    if (from.equals(to))
      throw new IllegalArgumentException(
          "Image operation requires a distinct destination identity");
  }

  public PixelBox forward(PixelBox box) {
    from.frame().requireSame(box.frame());
    PixelPoint p = forward(box.topLeft()),
        q = forward(box.topRight()),
        r = forward(box.bottomLeft()),
        s = forward(box.bottomRight());
    return new PixelBox(
        to.frame(),
        StrictMath.min(StrictMath.min(p.u(), q.u()), StrictMath.min(r.u(), s.u())),
        StrictMath.min(StrictMath.min(p.v(), q.v()), StrictMath.min(r.v(), s.v())),
        StrictMath.max(StrictMath.max(p.u(), q.u()), StrictMath.max(r.u(), s.u())),
        StrictMath.max(StrictMath.max(p.v(), q.v()), StrictMath.max(r.v(), s.v())));
  }

  public ImageTransform inverse() {
    double det = a * d - b * c;
    return new ImageTransform(
        to,
        from,
        d / det,
        -b / det,
        -c / det,
        a / det,
        (b * ty - d * tx) / det,
        (c * tx - a * ty) / det);
  }

  /** Apply this then next; image frame AND dimensions must match at the join. */
  public ImageTransform then(ImageTransform next) {
    to.requireSame(next.from);
    return new ImageTransform(
        from,
        next.to,
        next.a * a + next.b * c,
        next.a * b + next.b * d,
        next.c * a + next.d * c,
        next.c * b + next.d * d,
        next.a * tx + next.b * ty + next.tx,
        next.c * tx + next.d * ty + next.ty);
  }
}
