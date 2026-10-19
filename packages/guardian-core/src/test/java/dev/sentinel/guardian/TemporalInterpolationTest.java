package dev.sentinel.guardian;

import static dev.sentinel.guardian.TemporalFixtures.*;
import static org.junit.jupiter.api.Assertions.*;

import java.util.Optional;
import java.util.OptionalDouble;
import java.util.Random;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

class TemporalInterpolationTest {
  @Test
  void timestampedScalarIsUnavailableOutsideIntervalAndRejectsClocks() {
    assertEquals(4, Interpolation.scalar(2, time(10), 10, time(50), time(20)).getAsDouble());
    assertEquals(2, Interpolation.scalar(2, time(10), 10, time(50), time(10)).getAsDouble());
    assertEquals(10, Interpolation.scalar(2, time(10), 10, time(50), time(50)).getAsDouble());
    assertFalse(Interpolation.scalar(2, time(10), 10, time(50), time(51)).isPresent());
    assertThrows(
        IllegalArgumentException.class,
        () -> Interpolation.scalar(2, time(10), 10, new MonotonicTime("other", 50), time(20)));
  }

  @ParameterizedTest
  @CsvSource({"0,2", "0.25,4", "0.5,6", "1,10"})
  void scalarAndVectorAnalytical(double fraction, double expected) {
    assertEquals(expected, Interpolation.scalar(2, 10, fraction), 1e-12);
    assertEquals(
        expected, Interpolation.vector(world(2, 4, 6), world(10, 12, 14), fraction).x(), 1e-12);
  }

  @Test
  void timeRangeZeroSpanAndMismatches() {
    assertEquals(.25, Interpolation.fraction(time(10), time(50), time(20)).getAsDouble());
    assertFalse(Interpolation.fraction(time(10), time(10), time(10)).isPresent());
    assertFalse(Interpolation.fraction(time(10), time(50), time(9)).isPresent());
    assertFalse(Interpolation.fraction(time(10), time(50), time(51)).isPresent());
    assertThrows(
        IllegalArgumentException.class,
        () -> Interpolation.fraction(time(1), time(2), new MonotonicTime("x", 1)));
    assertThrows(
        IllegalArgumentException.class,
        () -> Interpolation.vector(world(0, 0, 0), device(1, 0, 0), .5));
    assertThrows(IllegalArgumentException.class, () -> Interpolation.scalar(0, 1, Double.NaN));
    assertThrows(IllegalArgumentException.class, () -> Interpolation.scalar(0, 1, 1.1));
    assertEquals(0, Interpolation.scalar(-Double.MAX_VALUE, Double.MAX_VALUE, .5));
  }

  @ParameterizedTest
  @CsvSource({"1.5707963267948966,0.7071067811865476,0.7071067811865476", "3.141592653589793,0,1"})
  void slerpKnownMidpoint(double angle, double x, double y) {
    Quaternion q = Interpolation.slerp(Quaternion.identity(), turn(0, 0, 1, angle), .5);
    Vector3 rotated = q.rotate(world(1, 0, 0));
    assertEquals(x, rotated.x(), 1e-12);
    assertEquals(y, rotated.y(), 1e-12);
  }

  @Test
  void antipodalAndTinyRotations() {
    Quaternion q = turn(1, 0, 0, .7), negative = new Quaternion(-q.w(), -q.x(), -q.y(), -q.z());
    Quaternion mid = Interpolation.slerp(q, negative, .5);
    assertEquals(1, StrictMath.abs(q.w() * mid.w() + q.x() * mid.x()), 1e-12);
    Quaternion tiny = Interpolation.slerp(Quaternion.identity(), turn(0, 0, 1, 1e-8), .5);
    assertEquals(2.5e-9, tiny.z(), 1e-17);
  }

  @Test
  void poseInterpolationPreservesEndpointsButNotInventedUncertainty() {
    DevicePoseEstimate a = pose(10, 2, Quaternion.identity()),
        b = pose(30, 10, turn(0, 0, 1, StrictMath.PI));
    assertSame(a, Interpolation.pose(a, b, time(10)).get());
    assertSame(b, Interpolation.pose(a, b, time(30)).get());
    DevicePoseEstimate mid = Interpolation.pose(a, b, time(20)).get();
    assertEquals(6, mid.transform().get().translationInToMeters().x());
    assertEquals(1, mid.transform().get().rotation().rotate(world(1, 0, 0)).y(), 1e-12);
    assertEquals(time(20), mid.time());
    assertFalse(mid.positionStdMeters().isPresent());
    assertEquals(.8, mid.confidence().value());
    assertFalse(Interpolation.pose(a, b, time(31)).isPresent());
    DevicePoseEstimate unknown =
        new DevicePoseEstimate(
            time(30),
            Optional.empty(),
            new Confidence(0),
            OptionalDouble.empty(),
            OptionalDouble.empty());
    assertFalse(Interpolation.pose(a, unknown, time(20)).isPresent());
  }

  @Test
  void randomizedSlerpNormEndpointsAndInterpolationBounds() {
    Random random = new Random(404);
    for (int i = 0; i < 500; i++) {
      Quaternion a =
          new Quaternion(
              random.nextDouble(), random.nextDouble(), random.nextDouble(), random.nextDouble());
      Quaternion b =
          new Quaternion(
              random.nextDouble(), random.nextDouble(), random.nextDouble(), random.nextDouble());
      Quaternion q = Interpolation.slerp(a, b, random.nextDouble());
      assertEquals(1, q.w() * q.w() + q.x() * q.x() + q.y() * q.y() + q.z() * q.z(), 1e-12);
      Vector3 p = world(1, 2, 3);
      assertEquals(
          0, a.rotate(p).subtract(Interpolation.slerp(a, b, 0).rotate(p)).magnitude(), 1e-12);
      assertEquals(
          0, b.rotate(p).subtract(Interpolation.slerp(a, b, 1).rotate(p)).magnitude(), 1e-12);
      double fraction = random.nextDouble();
      double value = Interpolation.scalar(-4, 20, fraction);
      assertTrue(value >= -4 && value <= 20);
      DevicePoseEstimate mid = Interpolation.pose(pose(0, -4, a), pose(100, 20, b), time(50)).get();
      assertEquals(8, mid.transform().get().translationInToMeters().x(), 1e-12);
    }
  }
}
