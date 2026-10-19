package dev.sentinel.guardian;

import java.util.OptionalDouble;

/** Constant-relative-velocity future CPA. Both values are available together or neither. */
public final class CpaResult {
  private final OptionalDouble seconds;
  private final OptionalDouble distanceMeters;

  private CpaResult(OptionalDouble seconds, OptionalDouble distanceMeters) {
    this.seconds = seconds;
    this.distanceMeters = distanceMeters;
  }

  static CpaResult known(double seconds, double distanceMeters) {
    return new CpaResult(
        OptionalDouble.of(NumericPolicy.nonNegative(seconds)),
        OptionalDouble.of(NumericPolicy.nonNegative(distanceMeters)));
  }

  public static CpaResult unavailable() {
    return new CpaResult(OptionalDouble.empty(), OptionalDouble.empty());
  }

  public boolean isValid() {
    return seconds.isPresent();
  }

  public OptionalDouble seconds() {
    return seconds;
  }

  public OptionalDouble distanceMeters() {
    return distanceMeters;
  }
}
