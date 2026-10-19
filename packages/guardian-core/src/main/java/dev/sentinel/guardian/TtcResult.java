package dev.sentinel.guardian;

import java.util.OptionalDouble;

/** Radial constant-closing-speed estimate, not a collision prediction. */
public final class TtcResult {
  private final OptionalDouble seconds;

  private TtcResult(OptionalDouble seconds) {
    this.seconds = seconds;
  }

  static TtcResult known(double seconds) {
    return new TtcResult(OptionalDouble.of(NumericPolicy.nonNegative(seconds)));
  }

  public static TtcResult unavailable() {
    return new TtcResult(OptionalDouble.empty());
  }

  public boolean isValid() {
    return seconds.isPresent();
  }

  public OptionalDouble seconds() {
    return seconds;
  }
}
