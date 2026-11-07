package dev.sentinel.guardian;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/** Deterministic plane-aligned tapered geometry, without motion or safety semantics. */
public final class CorridorGeometry {
  private CorridorGeometry() {}

  public static final class Corridor {
    private final Vector3 origin, forward, right;
    private final double near, far, nearWidth, farWidth;

    public Corridor(
        Vector3 origin,
        Vector3 forward,
        Vector3 right,
        double near,
        double far,
        double nearWidth,
        double farWidth) {
      origin.frame().requireSame(forward.frame());
      origin.frame().requireSame(right.frame());
      for (double value : new double[] {near, far, nearWidth, farWidth})
        NumericPolicy.finite(value);
      if (near < 0
          || far <= near
          || nearWidth <= 0
          || farWidth <= 0
          || StrictMath.abs(forward.magnitude() - 1) > 1e-8
          || StrictMath.abs(right.magnitude() - 1) > 1e-8
          || StrictMath.abs(forward.dot(right)) > 1e-8)
        throw new IllegalArgumentException("Invalid corridor basis or dimensions");
      this.origin = origin;
      this.forward = forward;
      this.right = right;
      this.near = near;
      this.far = far;
      this.nearWidth = nearWidth;
      this.farWidth = farWidth;
    }

    public Vector3 origin() {
      return origin;
    }

    public Vector3 forward() {
      return forward;
    }

    public Vector3 right() {
      return right;
    }

    public List<Vector3> polygon() {
      return Collections.unmodifiableList(
          Arrays.asList(
              origin.add(forward.multiply(near)).subtract(right.multiply(nearWidth)),
              origin.add(forward.multiply(near)).add(right.multiply(nearWidth)),
              origin.add(forward.multiply(far)).add(right.multiply(farWidth)),
              origin.add(forward.multiply(far)).subtract(right.multiply(farWidth))));
    }

    /** x=lateral right, y=forward. Signed Euclidean distance to the closed footprint. */
    public double[] locate(Vector3 point) {
      Vector3 delta = point.subtract(origin);
      double x = delta.dot(right);
      double y = delta.dot(forward);
      double t = (y - near) / (far - near);
      double width = nearWidth + t * (farWidth - nearWidth);
      boolean inside = y >= near && y <= far && StrictMath.abs(x) <= width;
      double[][] vertices = {
        {-nearWidth, near}, {nearWidth, near}, {farWidth, far}, {-farWidth, far}
      };
      double distance = Double.POSITIVE_INFINITY;
      for (int i = 0; i < 4; i++) {
        double[] a = vertices[i];
        double[] b = vertices[(i + 1) % 4];
        double dx = b[0] - a[0], dy = b[1] - a[1];
        double s =
            StrictMath.max(
                0, StrictMath.min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / (dx * dx + dy * dy)));
        distance = StrictMath.min(distance, StrictMath.hypot(x - a[0] - s * dx, y - a[1] - s * dy));
      }
      return new double[] {x, y, inside ? -distance : distance};
    }
  }

  public static Corridor onPlane(
      Vector3 cameraOrigin,
      Vector3 cameraForward,
      Vector3 planePoint,
      Vector3 normal,
      double near,
      double far,
      double nearWidth,
      double farWidth) {
    Vector3 up = normal.normalized();
    if (cameraOrigin.subtract(planePoint).dot(up) <= 0)
      throw new IllegalArgumentException("Plane normal must point toward camera above plane");
    Vector3 origin = cameraOrigin.subtract(up.multiply(cameraOrigin.subtract(planePoint).dot(up)));
    Vector3 forward = cameraForward.subtract(up.multiply(cameraForward.dot(up))).normalized();
    // CAMERA axes are right/down/forward. Up points against gravity.
    Vector3 right = forward.cross(up).normalized();
    return new Corridor(origin, forward, right, near, far, nearWidth, farWidth);
  }
}
