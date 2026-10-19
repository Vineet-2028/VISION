package dev.sentinel.guardian;

import static dev.sentinel.guardian.TemporalFixtures.*;
import static org.junit.jupiter.api.Assertions.*;

import java.util.Optional;
import java.util.Random;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

class ImuMotionTest {
  @ParameterizedTest
  @CsvSource({"0,0,0,9.80665", "3.141592653589793,0,0,-9.80665", "1.5707963267948966,0,9.80665,0"})
  void gravityStationaryUprightInvertedAndQuarterTurn(double roll, double x, double y, double z) {
    LinearAccelerationSample a =
        ImuMath.compensateGravity(
                new SpecificForceSample(time(0), device(x, y, z)),
                orientation(0, turn(1, 0, 0, roll)),
                new GravityModel(WORLD, 9.80665))
            .get();
    assertEquals(0, a.metersPerSecondSquared().magnitude(), 1e-12);
  }

  @Test
  void knownUpwardAccelerationAndAlignmentRequired() {
    LinearAccelerationSample a =
        ImuMath.compensateGravity(
                new SpecificForceSample(time(0), device(0, 0, 11.80665)),
                orientation(0, Quaternion.identity()),
                new GravityModel(WORLD, 9.80665))
            .get();
    assertEquals(2, a.metersPerSecondSquared().z(), 1e-12);
    assertThrows(IllegalArgumentException.class, () -> new GravityModel(WORLD, 0));
    assertThrows(
        IllegalArgumentException.class,
        () ->
            ImuMath.compensateGravity(
                new SpecificForceSample(time(1), device(0, 0, 10)),
                orientation(0, Quaternion.identity()),
                new GravityModel(WORLD, 9.8)));
  }

  @ParameterizedTest
  @CsvSource({"1,0,0,0,1,0,0,0,1", "0,1,0,0,0,1,1,0,0", "0,0,1,1,0,0,0,1,0"})
  void constantBodyRollPitchYaw(
      double wx,
      double wy,
      double wz,
      double x,
      double y,
      double z,
      double ex,
      double ey,
      double ez) {
    AngularVelocitySample rate =
        new AngularVelocitySample(
            time(0),
            device(wx * StrictMath.PI / 2, wy * StrictMath.PI / 2, wz * StrictMath.PI / 2));
    Quaternion q =
        ImuMath.propagate(orientation(0, Quaternion.identity()), rate, time(1000000000), 1000000000)
            .get()
            .rotation()
            .get();
    Vector3 result = q.rotate(world(x, y, z));
    assertEquals(ex, result.x(), 1e-12);
    assertEquals(ey, result.y(), 1e-12);
    assertEquals(ez, result.z(), 1e-12);
  }

  @Test
  void bodyRateRightMultipliesNoncommutingInitialRotation() {
    OrientationEstimate initial = orientation(0, turn(1, 0, 0, StrictMath.PI / 2));
    Quaternion result =
        ImuMath.propagate(initial, gyro(0, StrictMath.PI / 2), time(1000000000), 1000000000)
            .get()
            .rotation()
            .get();
    Vector3 rotated = result.rotate(world(1, 0, 0));
    assertEquals(0, rotated.x(), 1e-12);
    assertEquals(0, rotated.y(), 1e-12);
    assertEquals(1, rotated.z(), 1e-12);
  }

  @Test
  void zeroTinyAndRepeatedGyroSteps() {
    OrientationEstimate start = orientation(0, Quaternion.identity());
    assertSame(start, ImuMath.propagate(start, gyro(0, 0), time(0), 1).get());
    assertEquals(1, ImuMath.propagate(start, gyro(0, 0), time(1), 1).get().rotation().get().w());
    assertTrue(ImuMath.propagate(start, gyro(0, 1e-8), time(1), 1).get().rotation().get().z() > 0);
    OrientationEstimate current = start;
    for (int i = 0; i < 100; i++)
      current =
          ImuMath.propagate(
                  current,
                  gyro(i * 10000000L, StrictMath.PI / 2),
                  time((i + 1) * 10000000L),
                  10000000L)
              .get();
    assertEquals(1, current.rotation().get().rotate(world(1, 0, 0)).y(), 1e-12);
    assertFalse(ImuMath.propagate(start, gyro(0, 1), time(11), 10).isPresent());
    assertThrows(
        IllegalArgumentException.class, () -> ImuMath.propagate(start, gyro(1, 1), time(10), 10));
  }

  @Test
  void biasCorrectionAndFreshness() {
    VectorEstimate gyroBias =
        new VectorEstimate(
            DEVICE,
            VectorEstimate.Quantity.ANGULAR_VELOCITY_RADPS,
            Optional.of(device(0, 0, .2)),
            Optional.empty(),
            new Confidence(.9));
    GyroscopeBiasEstimate bias =
        new GyroscopeBiasEstimate(new TimedVectorEstimate(time(10), gyroBias));
    assertEquals(.8, ImuMath.correctGyro(gyro(15, 1), bias, 5).get().radiansPerSecond().z(), 1e-12);
    assertFalse(ImuMath.correctGyro(gyro(16, 1), bias, 5).isPresent());
    assertFalse(ImuMath.correctGyro(gyro(9, 1), bias, 5).isPresent());
    AccelerometerBiasEstimate ab =
        new AccelerometerBiasEstimate(
            new TimedVectorEstimate(
                time(0),
                new VectorEstimate(
                    DEVICE,
                    VectorEstimate.Quantity.SPECIFIC_FORCE_MPS2,
                    Optional.of(device(1, 2, 3)),
                    Optional.empty(),
                    new Confidence(.9))));
    Vector3 corrected =
        ImuMath.correctAccelerometer(new SpecificForceSample(time(0), device(3, 4, 5)), ab, 0)
            .get()
            .metersPerSecondSquared();
    assertEquals(2, corrected.x());
    assertEquals(2, corrected.y());
    assertEquals(2, corrected.z());
    assertThrows(
        IllegalArgumentException.class,
        () -> new GyroscopeBiasEstimate(new TimedVectorEstimate(time(0), ab.estimate())));
  }

  @Test
  void seededGyroIntegrationNormAndFiniteFailures() {
    Random random = new Random(405);
    OrientationEstimate q = orientation(0, Quaternion.identity());
    for (int i = 0; i < 1000; i++) {
      q =
          ImuMath.propagate(
                  q,
                  new AngularVelocitySample(
                      time(i * 1000000L),
                      device(random.nextGaussian(), random.nextGaussian(), random.nextGaussian())),
                  time((i + 1) * 1000000L),
                  1000000L)
              .get();
      Quaternion r = q.rotation().get();
      assertEquals(1, r.w() * r.w() + r.x() * r.x() + r.y() * r.y() + r.z() * r.z(), 1e-12);
    }
    assertThrows(IllegalArgumentException.class, () -> device(Double.NaN, 0, 0));
    assertThrows(
        IllegalArgumentException.class,
        () ->
            ImuMath.propagate(
                orientation(0, Quaternion.identity()),
                new AngularVelocitySample(time(0), device(Double.MAX_VALUE, Double.MAX_VALUE, 0)),
                time(Long.MAX_VALUE),
                Long.MAX_VALUE));
  }
}
