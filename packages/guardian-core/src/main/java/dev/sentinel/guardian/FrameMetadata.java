package dev.sentinel.guardian;

import java.util.Objects;
import java.util.Optional;

/** Timestamp is exposure midpoint in the synchronized sensor clock domain. */
public final class FrameMetadata {
  private final long sequence;
  private final FrameId imageFrame;
  private final MonotonicTime captureTime;
  private final Optional<WallClockTime> wallClockTime;
  private final int widthPixels;
  private final int heightPixels;
  private final Optional<CalibrationId> calibrationId;

  public FrameMetadata(
      long sequence,
      FrameId imageFrame,
      MonotonicTime captureTime,
      Optional<WallClockTime> wallClockTime,
      int widthPixels,
      int heightPixels) {
    this(
        sequence,
        imageFrame,
        captureTime,
        wallClockTime,
        widthPixels,
        heightPixels,
        Optional.empty());
  }

  public FrameMetadata(
      long sequence,
      FrameId imageFrame,
      MonotonicTime captureTime,
      Optional<WallClockTime> wallClockTime,
      int widthPixels,
      int heightPixels,
      Optional<CalibrationId> calibrationId) {
    this.calibrationId = Objects.requireNonNull(calibrationId, "calibrationId");
    if (sequence < 0 || widthPixels <= 0 || heightPixels <= 0)
      throw new IllegalArgumentException("Invalid frame dimensions or sequence");
    this.imageFrame = Objects.requireNonNull(imageFrame, "imageFrame");
    if (imageFrame.kind() != FrameKind.IMAGE)
      throw new IllegalArgumentException("Expected image frame");
    this.sequence = sequence;
    this.captureTime = Objects.requireNonNull(captureTime, "captureTime");
    this.wallClockTime = Objects.requireNonNull(wallClockTime, "wallClockTime");
    this.widthPixels = widthPixels;
    this.heightPixels = heightPixels;
  }

  public long sequence() {
    return sequence;
  }

  public FrameId imageFrame() {
    return imageFrame;
  }

  public MonotonicTime captureTime() {
    return captureTime;
  }

  public Optional<WallClockTime> wallClockTime() {
    return wallClockTime;
  }

  public int widthPixels() {
    return widthPixels;
  }

  public int heightPixels() {
    return heightPixels;
  }

  public Optional<CalibrationId> calibrationId() {
    return calibrationId;
  }
}
