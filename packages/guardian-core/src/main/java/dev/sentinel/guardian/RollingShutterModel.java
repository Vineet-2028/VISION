package dev.sentinel.guardian;

import java.util.Objects;
import java.util.Optional;

/**
 * Physical SENSOR image rows only. First-to-last row exposure-midpoint span, not exposure duration.
 */
public final class RollingShutterModel {
  public enum Kind {
    UNKNOWN,
    GLOBAL_SHUTTER,
    ROLLING_SHUTTER
  }

  public enum Scan {
    TOP_TO_BOTTOM,
    BOTTOM_TO_TOP
  }

  private final Kind kind;
  private final ImageSize image;
  private final Scan scan;
  private final MonotonicTime firstRowMidpoint;
  private final long readoutSpanNanos;

  public RollingShutterModel(
      Kind kind,
      ImageSize image,
      MonotonicTime firstRowMidpoint,
      long readoutSpanNanos,
      Scan scan) {
    this.kind = Objects.requireNonNull(kind, "kind");
    this.image = Objects.requireNonNull(image, "image");
    this.firstRowMidpoint = Objects.requireNonNull(firstRowMidpoint, "firstRowMidpoint");
    this.scan = Objects.requireNonNull(scan, "scan");
    if (readoutSpanNanos < 0
        || (kind != Kind.ROLLING_SHUTTER && readoutSpanNanos != 0)
        || (image.height() == 1 && readoutSpanNanos != 0))
      throw new IllegalArgumentException("Invalid readout span");
    if (readoutSpanNanos > Long.MAX_VALUE - firstRowMidpoint.nanos())
      throw new IllegalArgumentException("Readout timestamp overflow");
    this.readoutSpanNanos = readoutSpanNanos;
  }

  public Optional<MonotonicTime> timestampForImageRow(FrameId sensorImage, double y) {
    image.frame().requireSame(sensorImage);
    NumericPolicy.finite(y);
    if (y < .5 || y > image.height() - .5)
      throw new IllegalArgumentException("Row center outside sensor");
    if (kind == Kind.UNKNOWN) return Optional.empty();
    double fraction = image.height() == 1 ? 0 : (y - .5) / (image.height() - 1);
    if (scan == Scan.BOTTOM_TO_TOP) fraction = 1 - fraction;
    long offset =
        kind == Kind.GLOBAL_SHUTTER
            ? 0
            : fraction >= 1
                ? readoutSpanNanos
                : StrictMath.min(readoutSpanNanos, Math.round(fraction * readoutSpanNanos));
    return Optional.of(
        new MonotonicTime(firstRowMidpoint.clockId(), firstRowMidpoint.nanos() + offset));
  }

  public Kind kind() {
    return kind;
  }

  public long readoutSpanNanos() {
    return readoutSpanNanos;
  }

  /** Geometric frame-center exposure midpoint, rounded down to a nanosecond. */
  public Optional<MonotonicTime> frameMidpoint() {
    return kind == Kind.UNKNOWN
        ? Optional.empty()
        : Optional.of(
            new MonotonicTime(
                firstRowMidpoint.clockId(), firstRowMidpoint.nanos() + readoutSpanNanos / 2));
  }
}
