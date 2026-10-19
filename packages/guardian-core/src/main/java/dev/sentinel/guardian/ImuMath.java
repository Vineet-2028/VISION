package dev.sentinel.guardian;

import java.util.Optional;
import java.util.OptionalDouble;

/** Deterministic nominal operations; no drift correction, covariance propagation or clock reads. */
public final class ImuMath {
  private ImuMath() {}

  public static Optional<LinearAccelerationSample> compensateGravity(
      SpecificForceSample force, OrientationEstimate orientation, GravityModel gravity) {
    force.metersPerSecondSquared().frame().requireSame(orientation.from());
    gravity.worldGravity().frame().requireSame(orientation.to());
    force.time().requireSameClock(orientation.time());
    if (!force.time().equals(orientation.time()))
      throw new IllegalArgumentException("Align orientation to measurement time");
    if (!orientation.rotation().isPresent()) return Optional.empty();
    Vector3 rotated =
        orientation.rotation().get().rotateInto(force.metersPerSecondSquared(), orientation.to());
    return Optional.of(
        new LinearAccelerationSample(force.time(), rotated.add(gravity.worldGravity())));
  }

  public static Optional<AngularVelocitySample> correctGyro(
      AngularVelocitySample measured, GyroscopeBiasEstimate bias, long maxAgeNanos) {
    measured.radiansPerSecond().frame().requireSame(bias.estimate().frame());
    if (Temporal.age(measured.time(), bias.time(), maxAgeNanos, bias.estimate().value().isPresent())
        != Temporal.Age.FRESH) return Optional.empty();
    return Optional.of(
        new AngularVelocitySample(
            measured.time(), measured.radiansPerSecond().subtract(bias.estimate().value().get())));
  }

  public static Optional<SpecificForceSample> correctAccelerometer(
      SpecificForceSample measured, AccelerometerBiasEstimate bias, long maxAgeNanos) {
    measured.metersPerSecondSquared().frame().requireSame(bias.estimate().frame());
    if (Temporal.age(measured.time(), bias.time(), maxAgeNanos, bias.estimate().value().isPresent())
        != Temporal.Age.FRESH) return Optional.empty();
    return Optional.of(
        new SpecificForceSample(
            measured.time(),
            measured.metersPerSecondSquared().subtract(bias.estimate().value().get())));
  }

  /** Body rate sampled at interval start, held constant to end; caller supplies maximum gap. */
  public static Optional<OrientationEstimate> propagate(
      OrientationEstimate start,
      AngularVelocitySample bodyRate,
      MonotonicTime end,
      long maxGapNanos) {
    if (start.from().kind() != FrameKind.DEVICE || start.to().kind() != FrameKind.LOCAL_WORLD)
      throw new IllegalArgumentException("DEVICE->WORLD required");
    start.from().requireSame(bodyRate.radiansPerSecond().frame());
    start.time().requireSameClock(bodyRate.time());
    if (!start.time().equals(bodyRate.time()))
      throw new IllegalArgumentException("Rate must be evaluated at interval start");
    long nanos = end.elapsedNanosSince(start.time());
    if (maxGapNanos < 0) throw new IllegalArgumentException("Negative gap");
    if (nanos > maxGapNanos || !start.rotation().isPresent()) return Optional.empty();
    if (nanos == 0) return Optional.of(start);
    Vector3 w = bodyRate.radiansPerSecond();
    double speed = NumericPolicy.finite(w.magnitude()), dt = nanos / 1_000_000_000.0;
    double theta = NumericPolicy.finite(speed * dt), half = theta / 2;
    double scale = speed == 0 ? dt / 2 : StrictMath.sin(half) / speed;
    Quaternion increment =
        new Quaternion(StrictMath.cos(half), w.x() * scale, w.y() * scale, w.z() * scale);
    Quaternion result = start.rotation().get().multiply(increment);
    return Optional.of(
        new OrientationEstimate(
            start.from(),
            start.to(),
            end,
            Optional.of(result),
            OptionalDouble.empty(),
            start.confidence()));
  }
}
