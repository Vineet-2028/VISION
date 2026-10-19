package dev.sentinel.guardian;

import java.util.Optional;

/** Plane n dot (p-point)=0; unit normal fixes signed metric distance. */
public final class Plane3D {
  private final Vector3 point, normal;

  public Plane3D(Vector3 point, Vector3 normal) {
    point.frame().requireSame(normal.frame());
    this.point = point;
    this.normal = normal.normalized();
  }

  public Vector3 point() {
    return point;
  }

  public Vector3 normal() {
    return normal;
  }

  public FrameId frame() {
    return point.frame();
  }

  public double signedDistance(Vector3 p) {
    return p.subtract(point).dot(normal);
  }

  public Vector3 projectPoint(Vector3 p) {
    return p.subtract(normal.multiply(signedDistance(p)));
  }

  public Optional<Vector3> rayIntersection(Ray3D ray, GeometryPolicy policy) {
    frame().requireSame(ray.frame());
    try {
      double denominator = normal.dot(ray.direction());
      if (StrictMath.abs(denominator) <= policy.parallelEpsilon()) return Optional.empty();
      double t = -signedDistance(ray.origin()) / denominator;
      if (!Double.isFinite(t) || t < 0) return Optional.empty();
      return Optional.of(ray.pointAt(t));
    } catch (IllegalArgumentException numericFailure) {
      return Optional.empty();
    }
  }
}
