package dev.sentinel.guardian;

import java.util.Optional;
import java.util.OptionalDouble;

/** Closed-interval interpolation only. Input mismatch throws; outside interval is unavailable. */
public final class Interpolation {
  private Interpolation() {}

  public static OptionalDouble fraction(MonotonicTime a, MonotonicTime b, MonotonicTime query) {
    long span = b.elapsedNanosSince(a);
    a.requireSameClock(query);
    if (span == 0) return OptionalDouble.empty();
    if (query.nanos() < a.nanos() || query.nanos() > b.nanos()) return OptionalDouble.empty();
    return OptionalDouble.of((double) (query.nanos() - a.nanos()) / span);
  }

  public static double scalar(double a, double b, double alpha) {
    NumericPolicy.finite(a);
    NumericPolicy.finite(b);
    if (NumericPolicy.nonNegative(alpha) > 1)
      throw new IllegalArgumentException("Interpolation fraction");
    if (alpha == 0) return a;
    if (alpha == 1) return b;
    return NumericPolicy.finite((1 - alpha) * a + alpha * b);
  }

  public static Vector3 vector(Vector3 a, Vector3 b, double alpha) {
    a.frame().requireSame(b.frame());
    return new Vector3(
        a.frame(),
        scalar(a.x(), b.x(), alpha),
        scalar(a.y(), b.y(), alpha),
        scalar(a.z(), b.z(), alpha));
  }

  public static OptionalDouble scalar(
      double a, MonotonicTime ta, double b, MonotonicTime tb, MonotonicTime query) {
    NumericPolicy.finite(a);
    NumericPolicy.finite(b);
    OptionalDouble fraction = fraction(ta, tb, query);
    return fraction.isPresent()
        ? OptionalDouble.of(scalar(a, b, fraction.getAsDouble()))
        : OptionalDouble.empty();
  }

  public static Optional<Vector3> vector(
      Vector3 a, MonotonicTime ta, Vector3 b, MonotonicTime tb, MonotonicTime query) {
    a.frame().requireSame(b.frame());
    OptionalDouble f = fraction(ta, tb, query);
    return f.isPresent() ? Optional.of(vector(a, b, f.getAsDouble())) : Optional.empty();
  }

  public static Quaternion slerp(Quaternion a, Quaternion b, double alpha) {
    if (NumericPolicy.nonNegative(alpha) > 1)
      throw new IllegalArgumentException("Interpolation fraction");
    double dot = a.w() * b.w() + a.x() * b.x() + a.y() * b.y() + a.z() * b.z();
    double sign = dot < 0 ? -1 : 1;
    dot = StrictMath.min(1, StrictMath.abs(dot));
    double w0, w1;
    if (dot > 0.9995) {
      w0 = 1 - alpha;
      w1 = alpha * sign;
    } else {
      double theta = StrictMath.acos(dot), denom = StrictMath.sin(theta);
      w0 = StrictMath.sin((1 - alpha) * theta) / denom;
      w1 = sign * StrictMath.sin(alpha * theta) / denom;
    }
    return new Quaternion(
        w0 * a.w() + w1 * b.w(),
        w0 * a.x() + w1 * b.x(),
        w0 * a.y() + w1 * b.y(),
        w0 * a.z() + w1 * b.z());
  }

  public static Optional<DevicePoseEstimate> pose(
      DevicePoseEstimate a, DevicePoseEstimate b, MonotonicTime query) {
    OptionalDouble f = fraction(a.time(), b.time(), query);
    if (!f.isPresent() || !a.transform().isPresent() || !b.transform().isPresent())
      return Optional.empty();
    RigidTransform x = a.transform().get(), y = b.transform().get();
    x.from().requireSame(y.from());
    x.to().requireSame(y.to());
    if (query.equals(a.time())) return Optional.of(a);
    if (query.equals(b.time())) return Optional.of(b);
    return Optional.of(
        new DevicePoseEstimate(
            query,
            Optional.of(
                new RigidTransform(
                    x.from(),
                    x.to(),
                    slerp(x.rotation(), y.rotation(), f.getAsDouble()),
                    vector(x.translationInToMeters(), y.translationInToMeters(), f.getAsDouble()))),
            new Confidence(StrictMath.min(a.confidence().value(), b.confidence().value())),
            OptionalDouble.empty(),
            OptionalDouble.empty()));
  }

  public static Optional<OrientationEstimate> orientation(
      OrientationEstimate a, OrientationEstimate b, MonotonicTime query) {
    a.from().requireSame(b.from());
    a.to().requireSame(b.to());
    OptionalDouble f = fraction(a.time(), b.time(), query);
    if (!f.isPresent() || !a.rotation().isPresent() || !b.rotation().isPresent())
      return Optional.empty();
    if (query.equals(a.time())) return Optional.of(a);
    if (query.equals(b.time())) return Optional.of(b);
    return Optional.of(
        new OrientationEstimate(
            a.from(),
            a.to(),
            query,
            Optional.of(slerp(a.rotation().get(), b.rotation().get(), f.getAsDouble())),
            OptionalDouble.empty(),
            new Confidence(StrictMath.min(a.confidence().value(), b.confidence().value()))));
  }
}
