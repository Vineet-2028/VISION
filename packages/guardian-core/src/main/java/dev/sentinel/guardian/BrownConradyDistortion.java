package dev.sentinel.guardian;

import java.util.Optional;

/**
 * Brown-Conrady k1,k2,k3,p1,p2 in dimensionless camera-plane coordinates. A conservative
 * positive-Jacobian bound certifies injectivity on maxRadius. Bounded damped Newton inversion never
 * falls back to the distorted coordinate.
 */
public final class BrownConradyDistortion implements LensDistortionModel {
  private final double k1, k2, k3, p1, p2, maxRadius;

  public BrownConradyDistortion(
      double k1, double k2, double k3, double p1, double p2, double maxRadius) {
    this.k1 = NumericPolicy.finite(k1);
    this.k2 = NumericPolicy.finite(k2);
    this.k3 = NumericPolicy.finite(k3);
    this.p1 = NumericPolicy.finite(p1);
    this.p2 = NumericPolicy.finite(p2);
    if (NumericPolicy.finite(maxRadius) <= NumericPolicy.EPSILON)
      throw new IllegalArgumentException("Invalid calibrated radius");
    this.maxRadius = maxRadius;
    double r2 = NumericPolicy.finite(maxRadius * maxRadius);
    // Lower bound on the symmetric Jacobian's smallest eigenvalue over the disk.
    double lower =
        1
            + negativeTerm(k1, 3 * r2)
            + negativeTerm(k2, 5 * r2 * r2)
            + negativeTerm(k3, 7 * r2 * r2 * r2)
            - 8 * maxRadius * (StrictMath.abs(p1) + StrictMath.abs(p2));
    if (!Double.isFinite(lower) || lower <= NumericPolicy.EPSILON)
      throw new IllegalArgumentException(
          "Distortion domain not certified injective; reduce radius or choose another model");
  }

  private static double negativeTerm(double coefficient, double factor) {
    return coefficient < 0 ? coefficient * factor : 0;
  }

  @Override
  public String modelName() {
    return "brown_conrady";
  }

  public double k1() {
    return k1;
  }

  public double k2() {
    return k2;
  }

  public double k3() {
    return k3;
  }

  public double p1() {
    return p1;
  }

  public double p2() {
    return p2;
  }

  public double maxRadius() {
    return maxRadius;
  }

  @Override
  public Optional<CameraPlanePoint> distort(CameraPlanePoint ideal) {
    if (StrictMath.hypot(ideal.x(), ideal.y()) > maxRadius) return Optional.empty();
    try {
      return Optional.of(evaluate(ideal.frame(), ideal.x(), ideal.y()));
    } catch (IllegalArgumentException numericFailure) {
      return Optional.empty();
    }
  }

  private CameraPlanePoint evaluate(FrameId frame, double x, double y) {
    double r2 = x * x + y * y;
    double radial = 1 + r2 * (k1 + r2 * (k2 + r2 * k3));
    return new CameraPlanePoint(
        frame,
        x * radial + 2 * p1 * x * y + p2 * (r2 + 2 * x * x),
        y * radial + p1 * (r2 + 2 * y * y) + 2 * p2 * x * y);
  }

  @Override
  public Optional<CameraPlanePoint> undistort(CameraPlanePoint distorted, GeometryPolicy policy) {
    double x = distorted.x(), y = distorted.y();
    double radius = StrictMath.hypot(x, y);
    if (!Double.isFinite(radius)) return Optional.empty();
    if (radius > maxRadius) {
      double scale = maxRadius / radius;
      x *= scale;
      y *= scale;
    }
    try {
      for (int iteration = 0; iteration <= policy.maxIterations(); iteration++) {
        CameraPlanePoint estimate = evaluate(distorted.frame(), x, y);
        double ex = estimate.x() - distorted.x(), ey = estimate.y() - distorted.y();
        double residual = StrictMath.hypot(ex, ey);
        if (!Double.isFinite(residual)) return Optional.empty();
        if (residual <= policy.solverTolerance())
          return Optional.of(new CameraPlanePoint(distorted.frame(), x, y));
        if (iteration == policy.maxIterations()) return Optional.empty();
        double r2 = x * x + y * y,
            radial = 1 + r2 * (k1 + r2 * (k2 + r2 * k3)),
            g = k1 + r2 * (2 * k2 + 3 * k3 * r2);
        double a = radial + 2 * x * x * g + 2 * p1 * y + 6 * p2 * x;
        double b = 2 * x * y * g + 2 * p1 * x + 2 * p2 * y;
        double d = radial + 2 * y * y * g + 6 * p1 * y + 2 * p2 * x;
        double determinant = a * d - b * b;
        if (!Double.isFinite(determinant) || determinant <= NumericPolicy.EPSILON)
          return Optional.empty();
        double dx = (d * ex - b * ey) / determinant, dy = (a * ey - b * ex) / determinant;
        if (!Double.isFinite(dx) || !Double.isFinite(dy)) return Optional.empty();
        boolean accepted = false;
        double damping = 1;
        for (int attempt = 0; attempt < 12; attempt++) {
          double nx = x - damping * dx, ny = y - damping * dy;
          if (StrictMath.hypot(nx, ny) <= maxRadius) {
            CameraPlanePoint trial = evaluate(distorted.frame(), nx, ny);
            double next = StrictMath.hypot(trial.x() - distorted.x(), trial.y() - distorted.y());
            if (Double.isFinite(next) && next < residual) {
              x = nx;
              y = ny;
              accepted = true;
              break;
            }
          }
          damping *= 0.5;
        }
        if (!accepted) return Optional.empty();
      }
    } catch (IllegalArgumentException numericFailure) {
      return Optional.empty();
    }
    return Optional.empty();
  }
}
