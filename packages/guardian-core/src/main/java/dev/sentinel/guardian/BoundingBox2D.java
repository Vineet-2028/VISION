package dev.sentinel.guardian;

/** Normalized image-edge coordinates [0,1]; nonzero area, x right, y down. */
public final class BoundingBox2D {
  private final double minX;
  private final double minY;
  private final double maxX;
  private final double maxY;

  public BoundingBox2D(double minX, double minY, double maxX, double maxY) {
    NumericPolicy.nonNegative(minX);
    NumericPolicy.nonNegative(minY);
    NumericPolicy.finite(maxX);
    NumericPolicy.finite(maxY);
    if (maxX > 1 || maxY > 1 || maxX <= minX || maxY <= minY)
      throw new IllegalArgumentException("Invalid normalized box");
    this.minX = minX;
    this.minY = minY;
    this.maxX = maxX;
    this.maxY = maxY;
  }

  public double minX() {
    return minX;
  }

  public double minY() {
    return minY;
  }

  public double maxX() {
    return maxX;
  }

  public double maxY() {
    return maxY;
  }
}
