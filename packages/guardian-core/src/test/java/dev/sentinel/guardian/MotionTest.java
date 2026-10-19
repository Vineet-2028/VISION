package dev.sentinel.guardian;

import static org.junit.jupiter.api.Assertions.*;

import java.util.Random;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

class MotionTest {
  private static final FrameId W = new FrameId(FrameKind.LOCAL_WORLD, "world");

  private static Vector3 v(double x, double y, double z) {
    return new Vector3(W, x, y, z);
  }

  private static MonotonicTime t(long nanos) {
    return new MonotonicTime("sensor", nanos);
  }

  @Test
  void timestampsAreDirectionalAndClockSpecific() {
    assertEquals(2, t(3_000_000_000L).motionSecondsSince(t(1_000_000_000L)));
    assertEquals(0, t(5).elapsedNanosSince(t(5)));
    assertTrue(t(5).compareTo(t(4)) > 0);
    assertTrue(t(4).compareTo(t(5)) < 0);
    assertEquals(0, t(5).compareTo(t(5)));
    assertEquals(10, t(Long.MAX_VALUE).elapsedNanosSince(t(Long.MAX_VALUE - 10)));
    assertThrows(IllegalArgumentException.class, () -> t(-1));
    assertThrows(IllegalArgumentException.class, () -> t(4).elapsedNanosSince(t(5)));
    assertThrows(
        IllegalArgumentException.class,
        () -> t(5).elapsedNanosSince(new MonotonicTime("other", 4)));
    assertThrows(
        IllegalArgumentException.class, () -> t(5).compareTo(new MonotonicTime("other", 4)));
    assertThrows(IllegalArgumentException.class, () -> new MonotonicTime("", 0));
  }

  @Test
  void analyticalDifferentiation() {
    MathTest.xyz(Motion.velocity(v(1, 2, 3), t(0), v(5, 8, 1), t(2_000_000_000L)), 2, 3, -1);
    MathTest.xyz(Motion.acceleration(v(3, 0, -2), t(0), v(7, 4, 0), t(2_000_000_000L)), 2, 2, 1);
    MathTest.xyz(
        Motion.velocity(v(0, 0, 0), t(0), v(1e-6, 0, 0), t(NumericPolicy.MIN_DELTA_NANOS)),
        1,
        0,
        0);
  }

  @Test
  void invalidDifferentiationFails() {
    for (long later : new long[] {0, 1, NumericPolicy.MIN_DELTA_NANOS - 1}) {
      assertThrows(
          IllegalArgumentException.class,
          () -> Motion.velocity(v(0, 0, 0), t(0), v(1, 0, 0), t(later)));
      assertThrows(
          IllegalArgumentException.class,
          () -> Motion.acceleration(v(0, 0, 0), t(0), v(1, 0, 0), t(later)));
    }
    assertThrows(
        IllegalArgumentException.class, () -> Motion.velocity(v(0, 0, 0), t(5), v(1, 0, 0), t(4)));
    assertThrows(
        IllegalArgumentException.class,
        () ->
            Motion.velocity(
                v(0, 0, 0),
                t(0),
                new Vector3(new FrameId(FrameKind.CAMERA, "c"), 1, 0, 0),
                t(10000)));
  }

  @ParameterizedTest
  @CsvSource({
    "10,0,0,-2,0,0,2",
    "10,0,0,2,0,0,-2",
    "10,0,0,0,0,0,0",
    "10,0,0,0,20,0,0",
    "3,4,0,-3,-4,0,5"
  })
  void radialClosingCases(
      double x, double y, double z, double vx, double vy, double vz, double expected) {
    assertEquals(expected, Motion.closingSpeed(v(x, y, z), v(vx, vy, vz)).getAsDouble(), 1e-10);
  }

  @Test
  void movingUserAndSameDirection() {
    Vector3 relative = Motion.relativePosition(v(0, 2, 0), v(0, 12, 0));
    Vector3 velocity = Motion.relativeVelocity(v(0, 3, 0), v(0, 1, 0));
    MathTest.xyz(relative, 0, 10, 0);
    MathTest.xyz(velocity, 0, -2, 0);
    assertEquals(2, Motion.closingSpeed(relative, velocity).getAsDouble());
    assertEquals(5, Motion.radialTtc(relative, velocity).seconds().getAsDouble());
    MathTest.xyz(Motion.relativeVelocity(v(3, 0, 0), v(3, 0, 0)), 0, 0, 0);
    // Stationary object, moving user.
    assertEquals(
        5,
        Motion.closestApproach(relative, Motion.relativeVelocity(v(0, 2, 0), v(0, 0, 0)))
            .seconds()
            .getAsDouble());
  }

  @Test
  void nearCoincidenceAndTtcValidity() {
    assertFalse(Motion.closingSpeed(v(1e-8, 0, 0), v(-1, 0, 0)).isPresent());
    assertFalse(Motion.radialTtc(v(0, 0, 0), v(-1, 0, 0)).isValid());
    assertFalse(Motion.radialTtc(v(10, 0, 0), v(1, 0, 0)).isValid());
    assertFalse(Motion.radialTtc(v(10, 0, 0), v(0, 0, 0)).isValid());
    assertFalse(Motion.radialTtc(v(10, 0, 0), v(-1e-8, 0, 0)).isValid());
    assertFalse(Motion.radialTtc(v(1e308, 0, 0), v(-1e-5, 0, 0)).isValid());
    assertFalse(
        Motion.radialTtc(v(NumericPolicy.NEAR_ZERO_DISTANCE_METERS, 0, 0), v(-1, 0, 0)).isValid());
    assertFalse(
        Motion.radialTtc(v(1, 0, 0), v(-NumericPolicy.NEAR_ZERO_SPEED_MPS, 0, 0)).isValid());
  }

  @ParameterizedTest
  @CsvSource({
    "10,0,0,-2,0,0,5,0",
    "10,2,0,-2,0,0,5,2",
    "10,-10,0,-1,1,0,10,0",
    "10,-20,0,-1,1,0,15,7.0710678118654755",
    "0,10,0,0,-2,0,5,0",
    "0,0,0,1,0,0,0,0",
    "10,0,0,0,1,0,0,10"
  })
  void analyticalCpa(
      double x, double y, double z, double vx, double vy, double vz, double time, double distance) {
    CpaResult cpa = Motion.closestApproach(v(x, y, z), v(vx, vy, vz));
    assertTrue(cpa.isValid());
    assertEquals(time, cpa.seconds().getAsDouble(), 1e-10);
    assertEquals(distance, cpa.distanceMeters().getAsDouble(), 1e-10);
  }

  @Test
  void cpaCannotPredictAUniqueFutureMinimum() {
    assertFalse(Motion.closestApproach(v(10, 0, 0), v(0, 0, 0)).isValid());
    assertFalse(Motion.closestApproach(v(10, 0, 0), v(1e-8, 0, 0)).isValid());
    assertFalse(Motion.closestApproach(v(10, 0, 0), v(2, 0, 0)).isValid());
    assertFalse(Motion.closestApproach(v(0, 0, 0), v(0, 0, 0)).isValid());
  }

  @Test
  void ttcIsNotCpaOrCollision() {
    Vector3 r = v(10, 10, 0), velocity = v(-1, 0, 0);
    assertEquals(20, Motion.radialTtc(r, velocity).seconds().getAsDouble(), 1e-10);
    CpaResult cpa = Motion.closestApproach(r, velocity);
    assertEquals(10, cpa.seconds().getAsDouble(), 1e-10);
    assertEquals(10, cpa.distanceMeters().getAsDouble(), 1e-10);
  }

  @Test
  void allRelativeMathRejectsFrameMismatch() {
    Vector3 other = new Vector3(new FrameId(FrameKind.LOCAL_WORLD, "other"), 1, 0, 0);
    assertThrows(IllegalArgumentException.class, () -> Motion.relativePosition(v(1, 0, 0), other));
    assertThrows(IllegalArgumentException.class, () -> Motion.relativeVelocity(v(1, 0, 0), other));
    assertThrows(IllegalArgumentException.class, () -> Motion.closingSpeed(v(1, 0, 0), other));
    assertThrows(IllegalArgumentException.class, () -> Motion.radialTtc(v(1, 0, 0), other));
    assertThrows(IllegalArgumentException.class, () -> Motion.closestApproach(v(1, 0, 0), other));
  }

  @Test
  void bearingsUseFrameSpecificHorizontalPlanes() {
    assertEquals(0, Motion.horizontalBearing(v(0, 2, 0)).getAsDouble());
    assertEquals(StrictMath.PI / 2, Motion.horizontalBearing(v(2, 0, 0)).getAsDouble(), 1e-10);
    assertEquals(-StrictMath.PI / 4, Motion.horizontalBearing(v(-2, 2, 0)).getAsDouble(), 1e-10);
    assertFalse(Motion.horizontalBearing(v(0, 0, 5)).isPresent());
    Vector3 opticalForward = new Vector3(new FrameId(FrameKind.CAMERA, "c"), 0, 3, 5);
    assertEquals(0, Motion.horizontalBearing(opticalForward).getAsDouble());
    assertFalse(Motion.direction(v(0, 0, 0)).isPresent());
    MathTest.xyz(Motion.direction(v(3, 4, 0)).get(), .6, .8, 0);
  }

  @Test
  void cpaMinimumInvariantForSeededFiniteTrajectories() {
    Random random = new Random(2002);
    for (int i = 0; i < 200; i++) {
      Vector3 r = v(random.nextDouble() * 20, random.nextDouble() * 20, random.nextDouble() * 20);
      Vector3 velocity =
          v(-random.nextDouble() * 4, -random.nextDouble() * 4, -random.nextDouble() * 4);
      CpaResult cpa = Motion.closestApproach(r, velocity);
      assertTrue(cpa.isValid());
      double time = cpa.seconds().getAsDouble(), distance = cpa.distanceMeters().getAsDouble();
      assertTrue(time >= 0);
      assertTrue(distance >= 0);
      assertTrue(distance <= r.magnitude() + 1e-10);
      Vector3 nearest = r.add(velocity.multiply(time));
      assertEquals(0, nearest.dot(velocity), 1e-9);
      assertTrue(nearest.magnitude() <= r.add(velocity.multiply(time + 1)).magnitude() + 1e-10);
    }
  }
}
