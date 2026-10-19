package dev.sentinel.guardian;

/**
 * Nominal intersection with ground and ray provenance, no propagated accuracy claim. Callers must
 * separately retain calibration, extrinsics and pose uncertainty.
 */
public final class GroundIntersectionCandidate {
  private final Vector3 nominalPoint;
  private final GroundPlaneEstimate ground;
  private final Ray3D ray;

  GroundIntersectionCandidate(Vector3 nominalPoint, GroundPlaneEstimate ground, Ray3D ray) {
    this.nominalPoint = nominalPoint;
    this.ground = ground;
    this.ray = ray;
  }

  public Vector3 nominalPoint() {
    return nominalPoint;
  }

  public GroundPlaneEstimate ground() {
    return ground;
  }

  public Ray3D ray() {
    return ray;
  }
}
