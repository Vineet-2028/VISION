package dev.sentinel.guardian;

/** Radians only. Normalized range (-pi,pi]; difference means target minus source. */
public final class Angles {
  private Angles() {}

  public static double normalizeRadians(double angle) {
    double r = NumericPolicy.finite(angle) % (2 * StrictMath.PI);
    if (r <= -StrictMath.PI) r += 2 * StrictMath.PI;
    if (r > StrictMath.PI) r -= 2 * StrictMath.PI;
    return r == 0 ? 0 : r;
  }

  public static double shortestAngularDifference(double source, double target) {
    return normalizeRadians(normalizeRadians(target) - normalizeRadians(source));
  }
}
