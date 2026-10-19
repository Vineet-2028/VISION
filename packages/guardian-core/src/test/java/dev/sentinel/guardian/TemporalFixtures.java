package dev.sentinel.guardian;

import java.util.Optional;
import java.util.OptionalDouble;

final class TemporalFixtures {
  static final FrameId DEVICE = new FrameId(FrameKind.DEVICE, "timing-body");
  static final FrameId WORLD = new FrameId(FrameKind.LOCAL_WORLD, "timing-world");

  private TemporalFixtures() {}

  static MonotonicTime time(long nanos) {
    return new MonotonicTime("timing-clock", nanos);
  }

  static Vector3 world(double x, double y, double z) {
    return new Vector3(WORLD, x, y, z);
  }

  static Vector3 device(double x, double y, double z) {
    return new Vector3(DEVICE, x, y, z);
  }

  static Quaternion turn(double x, double y, double z, double radians) {
    double s = StrictMath.sin(radians / 2);
    return new Quaternion(StrictMath.cos(radians / 2), x * s, y * s, z * s);
  }

  static DevicePoseEstimate pose(long t, double x, Quaternion q) {
    return new DevicePoseEstimate(
        time(t),
        Optional.of(new RigidTransform(DEVICE, WORLD, q, world(x, 0, 0))),
        new Confidence(.8),
        OptionalDouble.of(.1),
        OptionalDouble.of(.02));
  }

  static OrientationEstimate orientation(long t, Quaternion q) {
    return new OrientationEstimate(
        DEVICE, WORLD, time(t), Optional.of(q), OptionalDouble.of(.02), new Confidence(.8));
  }

  static TimedVectorEstimate estimate(long t, VectorEstimate.Quantity quantity, double x) {
    return new TimedVectorEstimate(
        time(t),
        new VectorEstimate(
            WORLD, quantity, Optional.of(world(x, 0, 0)), Optional.empty(), new Confidence(.8)));
  }

  static AngularVelocitySample gyro(long t, double z) {
    return new AngularVelocitySample(time(t), device(0, 0, z));
  }
}
