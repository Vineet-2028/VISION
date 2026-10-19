package dev.sentinel.guardian;

/** Configured absolute innovation gate. No globally chosen sensor/hazard threshold. */
public final class OutlierGate {
  private OutlierGate() {}

  public static boolean accepts(double predicted, double measured, double limit) {
    NumericPolicy.finite(predicted);
    NumericPolicy.finite(measured);
    NumericPolicy.nonNegative(limit);
    return StrictMath.abs(measured - predicted) <= limit;
  }

  public static boolean accepts(Vector3 predicted, Vector3 measured, double limit) {
    predicted.frame().requireSame(measured.frame());
    NumericPolicy.nonNegative(limit);
    double dx = measured.x() - predicted.x(),
        dy = measured.y() - predicted.y(),
        dz = measured.z() - predicted.z();
    return StrictMath.hypot(StrictMath.hypot(dx, dy), dz) <= limit;
  }
}
