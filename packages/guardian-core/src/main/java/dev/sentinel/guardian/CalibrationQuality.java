package dev.sentinel.guardian;

import java.util.Objects;
import java.util.Optional;
import java.util.OptionalDouble;
import java.util.OptionalLong;

/**
 * Supplied evidence, not an automatic safety classification. Resolution lives in calibration
 * intrinsics.
 */
public final class CalibrationQuality {
  public enum State {
    UNKNOWN,
    VALID,
    DEGRADED,
    INVALID
  }

  private final State state;
  private final OptionalDouble rmsPixels;
  private final OptionalLong sampleCount;
  private final Optional<WallClockTime> calibratedAt;

  public CalibrationQuality(
      State state,
      OptionalDouble rmsPixels,
      OptionalLong sampleCount,
      Optional<WallClockTime> calibratedAt) {
    this.state = Objects.requireNonNull(state, "state");
    this.rmsPixels = Objects.requireNonNull(rmsPixels, "rmsPixels");
    this.sampleCount = Objects.requireNonNull(sampleCount, "sampleCount");
    this.calibratedAt = Objects.requireNonNull(calibratedAt, "calibratedAt");
    if (rmsPixels.isPresent()) NumericPolicy.nonNegative(rmsPixels.getAsDouble());
    if (sampleCount.isPresent() && sampleCount.getAsLong() < 1)
      throw new IllegalArgumentException("Invalid calibration sample count");
    if (state == State.VALID && (!rmsPixels.isPresent() || !sampleCount.isPresent()))
      throw new IllegalArgumentException("Valid calibration requires evidence");
  }

  public static CalibrationQuality unknown() {
    return new CalibrationQuality(
        State.UNKNOWN, OptionalDouble.empty(), OptionalLong.empty(), Optional.empty());
  }

  public State state() {
    return state;
  }

  public OptionalDouble rmsPixels() {
    return rmsPixels;
  }

  public OptionalLong sampleCount() {
    return sampleCount;
  }

  public Optional<WallClockTime> calibratedAt() {
    return calibratedAt;
  }
}
