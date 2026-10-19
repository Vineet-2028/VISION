package dev.sentinel.guardian;

import static dev.sentinel.guardian.TemporalFixtures.*;
import static org.junit.jupiter.api.Assertions.*;

import java.util.Optional;
import java.util.OptionalDouble;
import org.junit.jupiter.api.Test;

class SynchronizationTest {
  @Test
  void differentStreamClockIsRejectedBeforePoisoningHistory() {
    SensorSynchronizer s =
        new SensorSynchronizer(
            DEVICE, WORLD, 4, 100, 100, new SynchronizationPolicy(20, 0, false, false));
    s.addPose(pose(10, 0, Quaternion.identity()));
    AngularVelocitySample other =
        new AngularVelocitySample(new MonotonicTime("other", 10), device(0, 0, 1));
    assertThrows(IllegalArgumentException.class, () -> s.addGyro(other));
    assertEquals(TemporalAlignment.Mode.EXACT, s.at(time(10)).pose().mode());
    assertFalse(s.at(time(10)).angularVelocity().value().isPresent());
    s.addGyro(gyro(10, 2));
    assertEquals(2, s.at(time(10)).angularVelocity().value().get().radiansPerSecond().z());
    s.reset();
    s.addGyro(other);
    assertEquals(
        TemporalAlignment.Mode.EXACT,
        s.at(new MonotonicTime("other", 10)).angularVelocity().mode());
  }

  @Test
  void signedSourceAgesExposeFutureEndpoint() {
    PoseHistory h = new PoseHistory(2, 100, 100);
    h.add(pose(10, 0, Quaternion.identity()));
    h.add(pose(30, 20, Quaternion.identity()));
    TemporalAlignment<DevicePoseEstimate> aligned =
        h.at(time(20), new SynchronizationPolicy(20, 0, false, false));
    assertEquals(10, aligned.firstSourceAgeNanos().getAsLong());
    assertEquals(-10, aligned.lastSourceAgeNanos().getAsLong());
    assertFalse(
        h.at(time(40), new SynchronizationPolicy(20, 0, false, false))
            .firstSourceAgeNanos()
            .isPresent());
  }

  @Test
  void poseHistoryExactInterpolationAndBoundedNearest() {
    PoseHistory h = new PoseHistory(3, 100, 100);
    SynchronizationPolicy p = new SynchronizationPolicy(20, 5, true, false);
    assertEquals(TemporalAlignment.Mode.UNAVAILABLE, h.at(time(10), p).mode());
    DevicePoseEstimate first = pose(10, 0, Quaternion.identity());
    h.add(first);
    h.add(pose(30, 20, Quaternion.identity()));
    assertSame(first, h.at(time(10), p).value().get());
    TemporalAlignment<DevicePoseEstimate> mid = h.at(time(20), p);
    assertEquals(TemporalAlignment.Mode.INTERPOLATED, mid.mode());
    assertEquals(10, mid.value().get().transform().get().translationInToMeters().x());
    assertEquals(20, mid.interpolationSpanNanos());
    TemporalAlignment<DevicePoseEstimate> nearest = h.at(time(35), p);
    assertEquals(TemporalAlignment.Mode.NEAREST_ALLOWED, nearest.mode());
    assertEquals(time(30), nearest.value().get().time());
    assertEquals(TemporalAlignment.Mode.UNAVAILABLE, h.at(time(36), p).mode());
    assertEquals(TemporalAlignment.Mode.UNAVAILABLE, h.at(time(5), p).mode());
    assertEquals(
        TemporalAlignment.Mode.NEAREST_ALLOWED,
        h.at(time(5), new SynchronizationPolicy(20, 5, true, true)).mode());
  }

  @Test
  void invalidPoseIsAnInterpolationBarrierAndNoImplicitExtrapolation() {
    PoseHistory h = new PoseHistory(3, 100, 100);
    h.add(pose(0, 0, Quaternion.identity()));
    h.add(
        new DevicePoseEstimate(
            time(10),
            Optional.empty(),
            new Confidence(0),
            OptionalDouble.empty(),
            OptionalDouble.empty()));
    h.add(pose(20, 20, Quaternion.identity()));
    SynchronizationPolicy p = new SynchronizationPolicy(100, 100, true, true);
    assertFalse(h.at(time(5), p).value().isPresent());
    assertFalse(h.at(time(10), p).value().isPresent());
    assertFalse(
        h.at(time(25), new SynchronizationPolicy(100, 100, false, false)).value().isPresent());
    h.add(pose(30, 30, Quaternion.identity()));
    assertEquals(3, h.size());
    h.reset();
    assertEquals(0, h.size());
  }

  @Test
  void interpolationSpanLimitAndWrongFrames() {
    PoseHistory h = new PoseHistory(2, 100, 100);
    h.add(pose(0, 0, Quaternion.identity()));
    h.add(pose(100, 100, Quaternion.identity()));
    assertFalse(h.at(time(50), new SynchronizationPolicy(20, 5, true, true)).value().isPresent());
    assertThrows(
        IllegalArgumentException.class,
        () ->
            h.at(new MonotonicTime("other", 50), new SynchronizationPolicy(100, 0, false, false)));
    FrameId other = new FrameId(FrameKind.LOCAL_WORLD, "other");
    assertThrows(
        IllegalArgumentException.class,
        () ->
            h.add(
                new DevicePoseEstimate(
                    time(101),
                    Optional.of(
                        new RigidTransform(
                            DEVICE, other, Quaternion.identity(), new Vector3(other, 0, 0, 0))),
                    new Confidence(1),
                    OptionalDouble.empty(),
                    OptionalDouble.empty())));
  }

  @Test
  void synchronizerAlignsAllStreamsWithoutLatestShortcut() {
    SensorSynchronizer s =
        new SensorSynchronizer(
            DEVICE, WORLD, 10, 100, 100, new SynchronizationPolicy(20, 5, true, false));
    for (long t : new long[] {0, 20}) {
      s.addPose(pose(t, t, Quaternion.identity()));
      s.addOrientation(orientation(t, turn(0, 0, 1, t * StrictMath.PI / 40)));
      s.addGyro(gyro(t, t));
      s.addLinearAcceleration(new LinearAccelerationSample(time(t), world(t, 0, 0)));
    }
    SensorSynchronizer.Result r = s.at(time(10));
    assertEquals(SensorSynchronizer.Quality.ALIGNED, r.quality());
    assertEquals(10, r.angularVelocity().value().get().radiansPerSecond().z());
    assertEquals(10, r.linearAcceleration().value().get().metersPerSecondSquared().x());
    assertEquals(time(10), r.pose().value().get().time());
    assertEquals(TemporalAlignment.Mode.INTERPOLATED, r.orientation().mode());
    assertEquals(SensorSynchronizer.Quality.DEGRADED, s.at(time(25)).quality());
    assertEquals(SensorSynchronizer.Quality.UNAVAILABLE, s.at(time(26)).quality());
    s.reset();
    assertEquals(SensorSynchronizer.Quality.UNAVAILABLE, s.at(time(0)).quality());
  }

  @Test
  void alignedPoseFeedsExistingCameraGeometry() {
    PoseHistory h = new PoseHistory(2, 100, 100);
    h.add(pose(0, 0, Quaternion.identity()));
    h.add(pose(20, 2, Quaternion.identity()));
    DevicePoseEstimate aligned =
        h.at(time(10), new SynchronizationPolicy(20, 0, false, false)).value().get();
    CameraModel camera = GeometryFixtures.model();
    FrameMetadata frame =
        new FrameMetadata(
            0,
            GeometryFixtures.I,
            time(10),
            Optional.empty(),
            1000,
            1000,
            Optional.of(GeometryFixtures.ID));
    CameraExtrinsics extrinsics =
        new CameraExtrinsics(
            GeometryFixtures.ID,
            "timing-extrinsic",
            new RigidTransform(GeometryFixtures.C, DEVICE, Quaternion.identity(), device(0, 0, 0)));
    Ray3D ray =
        SpatialGeometry.pixelToWorldRay(
                GeometryFixtures.pixel(500, 500), frame, camera, extrinsics, aligned)
            .get();
    assertEquals(1, ray.origin().x());
    assertEquals(time(10), ray.time().get());
    DevicePoseEstimate nearest =
        h.at(time(21), new SynchronizationPolicy(20, 1, true, false)).value().get();
    FrameMetadata later =
        new FrameMetadata(
            1,
            GeometryFixtures.I,
            time(21),
            Optional.empty(),
            1000,
            1000,
            Optional.of(GeometryFixtures.ID));
    assertThrows(
        IllegalArgumentException.class,
        () ->
            SpatialGeometry.pixelToWorldRay(
                GeometryFixtures.pixel(500, 500), later, camera, extrinsics, nearest));
  }
}
