package dev.sentinel.guardian;

/** Unit quaternion (w,x,y,z), Hamilton product and active right-handed rotations. */
public final class Quaternion {
  private final double w;
  private final double x;
  private final double y;
  private final double z;

  public Quaternion(double w, double x, double y, double z) {
    NumericPolicy.finite(w);
    NumericPolicy.finite(x);
    NumericPolicy.finite(y);
    NumericPolicy.finite(z);
    double scale =
        StrictMath.max(
            StrictMath.max(StrictMath.abs(w), StrictMath.abs(x)),
            StrictMath.max(StrictMath.abs(y), StrictMath.abs(z)));
    if (scale <= NumericPolicy.EPSILON) throw new IllegalArgumentException("Near-zero quaternion");
    double sw = w / scale, sx = x / scale, sy = y / scale, sz = z / scale;
    double norm = StrictMath.sqrt(sw * sw + sx * sx + sy * sy + sz * sz);
    this.w = sw / norm;
    this.x = sx / norm;
    this.y = sy / norm;
    this.z = sz / norm;
  }

  public static Quaternion identity() {
    return new Quaternion(1, 0, 0, 0);
  }

  public Quaternion conjugate() {
    return new Quaternion(w, -x, -y, -z);
  }

  /** this * right applies right first, then this. */
  public Quaternion multiply(Quaternion right) {
    return new Quaternion(
        w * right.w() - x * right.x() - y * right.y() - z * right.z(),
        w * right.x() + x * right.w() + y * right.z() - z * right.y(),
        w * right.y() - x * right.z() + y * right.w() + z * right.x(),
        w * right.z() + x * right.y() - y * right.x() + z * right.w());
  }

  /** Active rotation inside the same coordinate frame. */
  public Vector3 rotate(Vector3 vector) {
    return rotateInto(vector, vector.frame());
  }

  public Vector3 inverseRotate(Vector3 vector) {
    return conjugate().rotate(vector);
  }

  Vector3 rotateInto(Vector3 v, FrameId destination) {
    // Rotation matrix avoids allocating intermediate quaternion/vector products.
    return new Vector3(
        destination,
        (1 - 2 * (y * y + z * z)) * v.x()
            + 2 * (x * y - z * w) * v.y()
            + 2 * (x * z + y * w) * v.z(),
        2 * (x * y + z * w) * v.x()
            + (1 - 2 * (x * x + z * z)) * v.y()
            + 2 * (y * z - x * w) * v.z(),
        2 * (x * z - y * w) * v.x()
            + 2 * (y * z + x * w) * v.y()
            + (1 - 2 * (x * x + y * y)) * v.z());
  }

  public double w() {
    return w;
  }

  public double x() {
    return x;
  }

  public double y() {
    return y;
  }

  public double z() {
    return z;
  }
}
