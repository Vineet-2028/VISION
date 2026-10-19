package dev.sentinel.guardian;

/** Numerical degeneracy limits, not hazard or sensor accuracy thresholds. */
public final class NumericPolicy {
  public static final double EPSILON = 1e-12;
  public static final long MIN_DELTA_NANOS = 1000;
  public static final double NEAR_ZERO_DISTANCE_METERS = 1e-6;
  public static final double NEAR_ZERO_SPEED_MPS = 1e-6;

  private NumericPolicy() {}

  public static double finite(double value) {
    if (!Double.isFinite(value)) throw new IllegalArgumentException("Value must be finite");
    return value;
  }

  public static double nonNegative(double value) {
    if (finite(value) < 0) throw new IllegalArgumentException("Value must be nonnegative");
    return value;
  }

  static double divisor(double value) {
    if (StrictMath.abs(finite(value)) <= EPSILON)
      throw new IllegalArgumentException("Near-zero divisor");
    return value;
  }

  static String identity(String value) {
    if (value == null || value.trim().isEmpty())
      throw new IllegalArgumentException("Identity must not be blank");
    return value;
  }
}
