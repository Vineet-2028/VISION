package dev.sentinel.guardian;

import java.util.Optional;
import java.util.OptionalDouble;

/** Deterministic raw kinematics in one fixed frame, with SI units throughout. */
public final class Motion {
  private Motion() {}

  public static Vector3 velocity(
      Vector3 earlierPosition, MonotonicTime earlier, Vector3 laterPosition, MonotonicTime later) {
    return laterPosition.subtract(earlierPosition).divide(later.motionSecondsSince(earlier));
  }

  public static Vector3 acceleration(
      Vector3 earlierVelocity, MonotonicTime earlier, Vector3 laterVelocity, MonotonicTime later) {
    return laterVelocity.subtract(earlierVelocity).divide(later.motionSecondsSince(earlier));
  }

  public static Vector3 relativePosition(Vector3 userPosition, Vector3 objectPosition) {
    return objectPosition.subtract(userPosition);
  }

  public static Vector3 relativeVelocity(Vector3 userVelocity, Vector3 objectVelocity) {
    return objectVelocity.subtract(userVelocity);
  }

  public static OptionalDouble closingSpeed(Vector3 relativePosition, Vector3 relativeVelocity) {
    relativePosition.frame().requireSame(relativeVelocity.frame());
    double distance = relativePosition.magnitude();
    if (distance <= NumericPolicy.NEAR_ZERO_DISTANCE_METERS) return OptionalDouble.empty();
    // Algebraically -(r dot v)/|r|, avoids overflowing the unscaled dot product.
    return OptionalDouble.of(
        NumericPolicy.finite(-relativePosition.divide(distance).dot(relativeVelocity)));
  }

  public static TtcResult radialTtc(Vector3 relativePosition, Vector3 relativeVelocity) {
    OptionalDouble speed = closingSpeed(relativePosition, relativeVelocity);
    if (!speed.isPresent() || speed.getAsDouble() <= NumericPolicy.NEAR_ZERO_SPEED_MPS)
      return TtcResult.unavailable();
    double seconds = relativePosition.magnitude() / speed.getAsDouble();
    return Double.isFinite(seconds) ? TtcResult.known(seconds) : TtcResult.unavailable();
  }

  public static CpaResult closestApproach(Vector3 relativePosition, Vector3 relativeVelocity) {
    relativePosition.frame().requireSame(relativeVelocity.frame());
    double speed = relativeVelocity.magnitude();
    if (speed <= NumericPolicy.NEAR_ZERO_SPEED_MPS) return CpaResult.unavailable();
    // -(r dot v)/|v|^2, factored to avoid overflow in the squared speed.
    double seconds = -relativePosition.dot(relativeVelocity.divide(speed)) / speed;
    if (!Double.isFinite(seconds) || seconds < 0) return CpaResult.unavailable();
    return CpaResult.known(
        seconds, relativePosition.add(relativeVelocity.multiply(seconds)).magnitude());
  }

  public static Optional<Vector3> direction(Vector3 relativePosition) {
    double distance = relativePosition.magnitude();
    return distance <= NumericPolicy.NEAR_ZERO_DISTANCE_METERS
        ? Optional.empty()
        : Optional.of(relativePosition.divide(distance));
  }

  /** atan2(right, forward): CAMERA x/z; DEVICE and LOCAL_WORLD x/y. No pose is inferred. */
  public static OptionalDouble horizontalBearing(Vector3 relativePosition) {
    double forward =
        relativePosition.frame().kind() == FrameKind.CAMERA
            ? relativePosition.z()
            : relativePosition.y();
    if (StrictMath.hypot(relativePosition.x(), forward) <= NumericPolicy.NEAR_ZERO_DISTANCE_METERS)
      return OptionalDouble.empty();
    return OptionalDouble.of(StrictMath.atan2(relativePosition.x(), forward));
  }
}
