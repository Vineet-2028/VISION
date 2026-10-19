package dev.sentinel.guardian;

/** Mathematical guards and bounded inverse solver controls, not safety/quality thresholds. */
public final class GeometryPolicy {
  private final double nearPlaneMeters;
  private final double parallelEpsilon;
  private final int maxIterations;
  private final double solverTolerance;

  public GeometryPolicy(
      double nearPlaneMeters, double parallelEpsilon, int maxIterations, double solverTolerance) {
    if (NumericPolicy.finite(nearPlaneMeters) <= 0
        || NumericPolicy.finite(parallelEpsilon) <= 0
        || parallelEpsilon >= 1
        || maxIterations < 1
        || maxIterations > 1000
        || NumericPolicy.finite(solverTolerance) <= 0
        || solverTolerance >= 1) throw new IllegalArgumentException("Invalid geometry policy");
    this.nearPlaneMeters = nearPlaneMeters;
    this.parallelEpsilon = parallelEpsilon;
    this.maxIterations = maxIterations;
    this.solverTolerance = solverTolerance;
  }

  public static GeometryPolicy defaults() {
    return new GeometryPolicy(
        NumericPolicy.NEAR_ZERO_DISTANCE_METERS, NumericPolicy.EPSILON, 30, 1e-10);
  }

  public double nearPlaneMeters() {
    return nearPlaneMeters;
  }

  public double parallelEpsilon() {
    return parallelEpsilon;
  }

  public int maxIterations() {
    return maxIterations;
  }

  public double solverTolerance() {
    return solverTolerance;
  }
}
