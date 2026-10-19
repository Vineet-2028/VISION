package dev.sentinel.guardian;

/** Bounded score, NOT a calibrated probability unless the producer establishes calibration. */
public final class Confidence {
  private final double value;

  public Confidence(double value) {
    NumericPolicy.nonNegative(value);
    if (value > 1) throw new IllegalArgumentException("Confidence exceeds one");
    this.value = value;
  }

  public double value() {
    return value;
  }
}
