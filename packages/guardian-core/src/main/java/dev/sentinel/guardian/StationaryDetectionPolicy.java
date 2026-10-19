package dev.sentinel.guardian;

/** All physical limits supplied by caller and require later device validation. */
public final class StationaryDetectionPolicy {
  final int minimumSamples;
  final long minimumSpanNanos, maximumGapNanos;
  final double maxGyro, gravityMagnitude, maxGravityDeviation, maxForceVariance;

  public StationaryDetectionPolicy(
      int minimumSamples,
      long minimumSpanNanos,
      long maximumGapNanos,
      double maxGyro,
      double gravityMagnitude,
      double maxGravityDeviation,
      double maxForceVariance) {
    if (minimumSamples < 2
        || minimumSpanNanos < 1
        || maximumGapNanos < 1
        || NumericPolicy.finite(gravityMagnitude) <= 0)
      throw new IllegalArgumentException("Invalid stationary window");
    this.minimumSamples = minimumSamples;
    this.minimumSpanNanos = minimumSpanNanos;
    this.maximumGapNanos = maximumGapNanos;
    this.maxGyro = NumericPolicy.nonNegative(maxGyro);
    this.gravityMagnitude = gravityMagnitude;
    this.maxGravityDeviation = NumericPolicy.nonNegative(maxGravityDeviation);
    this.maxForceVariance = NumericPolicy.nonNegative(maxForceVariance);
  }
}
