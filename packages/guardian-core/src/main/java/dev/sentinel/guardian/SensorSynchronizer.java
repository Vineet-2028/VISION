package dev.sentinel.guardian;

import java.util.Optional;

/** All mutation and lookup belong to one owner thread; no background work or shared locks. */
public final class SensorSynchronizer {
  public enum Quality {
    ALIGNED,
    DEGRADED,
    UNAVAILABLE
  }

  public static final class Result {
    private final TemporalAlignment<DevicePoseEstimate> pose;
    private final TemporalAlignment<OrientationEstimate> orientation;
    private final TemporalAlignment<AngularVelocitySample> gyro;
    private final TemporalAlignment<LinearAccelerationSample> acceleration;

    private Result(
        TemporalAlignment<DevicePoseEstimate> p,
        TemporalAlignment<OrientationEstimate> o,
        TemporalAlignment<AngularVelocitySample> g,
        TemporalAlignment<LinearAccelerationSample> a) {
      pose = p;
      orientation = o;
      gyro = g;
      acceleration = a;
    }

    public TemporalAlignment<DevicePoseEstimate> pose() {
      return pose;
    }

    public TemporalAlignment<OrientationEstimate> orientation() {
      return orientation;
    }

    public TemporalAlignment<AngularVelocitySample> angularVelocity() {
      return gyro;
    }

    public TemporalAlignment<LinearAccelerationSample> linearAcceleration() {
      return acceleration;
    }

    public Quality quality() {
      if (!pose.value().isPresent()
          && !orientation.value().isPresent()
          && !gyro.value().isPresent()
          && !acceleration.value().isPresent()) return Quality.UNAVAILABLE;
      if (aligned(pose) && aligned(orientation) && aligned(gyro) && aligned(acceleration))
        return Quality.ALIGNED;
      return Quality.DEGRADED;
    }

    private static boolean aligned(TemporalAlignment<?> x) {
      return x.mode() == TemporalAlignment.Mode.EXACT
          || x.mode() == TemporalAlignment.Mode.INTERPOLATED;
    }
  }

  private final FrameId device, world;
  private final PoseHistory poses;
  private final SampleBuffer<OrientationEstimate> orientations;
  private final SampleBuffer<AngularVelocitySample> gyros;
  private final SampleBuffer<LinearAccelerationSample> accelerations;
  private final SynchronizationPolicy policy;
  private String clock;

  public SensorSynchronizer(
      FrameId device,
      FrameId world,
      int capacity,
      long retention,
      long lateWindow,
      SynchronizationPolicy policy) {
    if (device.kind() != FrameKind.DEVICE || world.kind() != FrameKind.LOCAL_WORLD)
      throw new IllegalArgumentException("DEVICE/WORLD required");
    this.device = device;
    this.world = world;
    this.policy = java.util.Objects.requireNonNull(policy, "policy");
    poses = new PoseHistory(capacity, retention, lateWindow);
    orientations = new SampleBuffer<>(capacity, retention, lateWindow);
    gyros = new SampleBuffer<>(capacity, retention, lateWindow);
    accelerations = new SampleBuffer<>(capacity, retention, lateWindow);
  }

  public SampleBuffer.Insertion addPose(DevicePoseEstimate p) {
    checkClock(p.time());
    if (p.transform().isPresent()) {
      device.requireSame(p.transform().get().from());
      world.requireSame(p.transform().get().to());
    }
    return inserted(poses.add(p), p.time());
  }

  public SampleBuffer.Insertion addOrientation(OrientationEstimate o) {
    checkClock(o.time());
    device.requireSame(o.from());
    world.requireSame(o.to());
    return inserted(orientations.add(o), o.time());
  }

  public SampleBuffer.Insertion addGyro(AngularVelocitySample g) {
    checkClock(g.time());
    device.requireSame(g.radiansPerSecond().frame());
    return inserted(gyros.add(g), g.time());
  }

  public SampleBuffer.Insertion addLinearAcceleration(LinearAccelerationSample a) {
    checkClock(a.time());
    world.requireSame(a.metersPerSecondSquared().frame());
    return inserted(accelerations.add(a), a.time());
  }

  public Result at(FrameMetadata frame) {
    return at(frame.captureTime());
  }

  public Result at(MonotonicTime time) {
    checkClock(time);
    return new Result(
        poses.at(time, policy),
        TemporalLookup.lookup(
            orientations, time, policy, o -> o.rotation().isPresent(), Interpolation::orientation),
        TemporalLookup.lookup(
            gyros,
            time,
            policy,
            g -> true,
            (a, b, t) ->
                Optional.of(
                    new AngularVelocitySample(
                        t,
                        Interpolation.vector(
                                a.radiansPerSecond(), a.time(), b.radiansPerSecond(), b.time(), t)
                            .get()))),
        TemporalLookup.lookup(
            accelerations,
            time,
            policy,
            a -> true,
            (a, b, t) ->
                Optional.of(
                    new LinearAccelerationSample(
                        t,
                        Interpolation.vector(
                                a.metersPerSecondSquared(),
                                a.time(),
                                b.metersPerSecondSquared(),
                                b.time(),
                                t)
                            .get()))));
  }

  public void reset() {
    poses.reset();
    orientations.reset();
    gyros.reset();
    accelerations.reset();
    clock = null;
  }

  private void checkClock(MonotonicTime time) {
    java.util.Objects.requireNonNull(time, "time");
    if (clock != null && !clock.equals(time.clockId()))
      throw new IllegalArgumentException(
          "Map all streams to one clock or reset before a new session");
  }

  private SampleBuffer.Insertion inserted(SampleBuffer.Insertion status, MonotonicTime time) {
    if (status == SampleBuffer.Insertion.ACCEPTED
        || status == SampleBuffer.Insertion.ACCEPT_AND_REORDER) clock = time.clockId();
    return status;
  }
}
