package dev.sentinel.guardian;

/** Approximate corner-ray bounds; distorted edges can have interior extrema. No metric size. */
public final class AngularExtent {
  private final double leftRadians, rightRadians, topRadians, bottomRadians;

  AngularExtent(double left, double right, double top, double bottom) {
    leftRadians = NumericPolicy.finite(left);
    rightRadians = NumericPolicy.finite(right);
    topRadians = NumericPolicy.finite(top);
    bottomRadians = NumericPolicy.finite(bottom);
  }

  public double leftRadians() {
    return leftRadians;
  }

  public double rightRadians() {
    return rightRadians;
  }

  public double topRadians() {
    return topRadians;
  }

  public double bottomRadians() {
    return bottomRadians;
  }
}
