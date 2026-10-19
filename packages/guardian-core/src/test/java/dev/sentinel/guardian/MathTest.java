package dev.sentinel.guardian;

import static org.junit.jupiter.api.Assertions.*;

import java.util.Random;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

class MathTest {
  private static final FrameId WORLD = new FrameId(FrameKind.LOCAL_WORLD, "session");
  private static final FrameId CAMERA = new FrameId(FrameKind.CAMERA, "rear");
  private static final FrameId DEVICE = new FrameId(FrameKind.DEVICE, "body");
  private static final double TOL = 1e-10;

  static void xyz(Vector3 actual, double x, double y, double z) {
    assertEquals(x, actual.x(), TOL);
    assertEquals(y, actual.y(), TOL);
    assertEquals(z, actual.z(), TOL);
  }

  @Test
  void vector2Operations() {
    Vector2 a = new Vector2(WORLD, 3, 4), b = new Vector2(WORLD, -1, 2);
    assertEquals(2, a.add(b).x());
    assertEquals(6, a.add(b).y());
    assertEquals(4, a.subtract(b).x());
    assertEquals(2, a.subtract(b).y());
    assertEquals(6, a.multiply(2).x());
    assertEquals(8, a.multiply(2).y());
    assertEquals(1.5, a.divide(2).x());
    assertEquals(2, a.divide(2).y());
    assertEquals(5, a.dot(b));
    assertEquals(5, a.magnitude());
    assertEquals(25, a.squaredMagnitude());
    assertEquals(20, a.squaredDistance(b));
    assertEquals(StrictMath.sqrt(20), a.distance(b), TOL);
    assertEquals(.6, a.normalized().x(), TOL);
    assertEquals(.8, a.normalized().y(), TOL);
  }

  @Test
  void vector3Operations() {
    Vector3 a = new Vector3(WORLD, 1, 2, 3), b = new Vector3(WORLD, 4, -2, 1);
    xyz(a.add(b), 5, 0, 4);
    xyz(a.subtract(b), -3, 4, 2);
    xyz(a.multiply(2), 2, 4, 6);
    xyz(a.divide(2), .5, 1, 1.5);
    assertEquals(3, a.dot(b));
    xyz(a.cross(b), 8, 11, -10);
    assertEquals(14, a.squaredMagnitude());
    assertEquals(StrictMath.sqrt(14), a.magnitude(), TOL);
    assertEquals(29, a.squaredDistance(b));
    assertEquals(StrictMath.sqrt(29), a.distance(b), TOL);
    assertEquals(1, a.normalized().magnitude(), TOL);
  }

  @Test
  void rightHandedCrossProduct() {
    xyz(new Vector3(WORLD, 1, 0, 0).cross(new Vector3(WORLD, 0, 1, 0)), 0, 0, 1);
  }

  @Test
  void vectorDegeneracy() {
    assertThrows(IllegalArgumentException.class, () -> new Vector2(WORLD, 0, 0).normalized());
    assertThrows(
        IllegalArgumentException.class, () -> new Vector3(WORLD, 1e-14, 0, 0).normalized());
    assertThrows(IllegalArgumentException.class, () -> new Vector3(WORLD, 0, 0, 0).normalized());
    assertThrows(IllegalArgumentException.class, () -> new Vector2(WORLD, 1, 0).divide(0));
    assertThrows(
        IllegalArgumentException.class,
        () -> new Vector3(WORLD, 1, 0, 0).divide(NumericPolicy.EPSILON));
  }

  @ParameterizedTest
  @ValueSource(doubles = {Double.NaN, Double.POSITIVE_INFINITY, Double.NEGATIVE_INFINITY})
  void nonFiniteRejected(double v) {
    assertThrows(IllegalArgumentException.class, () -> new Vector2(WORLD, v, 0));
    assertThrows(IllegalArgumentException.class, () -> new Vector3(WORLD, 0, v, 0));
    assertThrows(IllegalArgumentException.class, () -> new Vector3(WORLD, 1, 0, 0).multiply(v));
    assertThrows(IllegalArgumentException.class, () -> new Quaternion(v, 0, 0, 0));
  }

  @Test
  void overflowIsExplicitAndHypotAvoidsUnnecessaryOverflow() {
    Vector3 huge = new Vector3(WORLD, 1e200, 1e200, 0);
    assertTrue(Double.isFinite(huge.magnitude()));
    assertEquals(1, huge.normalized().magnitude(), TOL);
    assertThrows(IllegalArgumentException.class, huge::squaredMagnitude);
    assertThrows(IllegalArgumentException.class, () -> huge.multiply(Double.MAX_VALUE));
    assertThrows(
        IllegalArgumentException.class,
        () -> new Vector2(WORLD, Double.MAX_VALUE, 0).add(new Vector2(WORLD, Double.MAX_VALUE, 0)));
  }

  @Test
  void framesAndInstancesCannotMix() {
    Vector3 a = new Vector3(WORLD, 1, 0, 0), b = new Vector3(CAMERA, 1, 0, 0);
    assertThrows(IllegalArgumentException.class, () -> a.add(b));
    assertThrows(IllegalArgumentException.class, () -> a.subtract(b));
    assertThrows(IllegalArgumentException.class, () -> a.dot(b));
    assertThrows(IllegalArgumentException.class, () -> a.cross(b));
    assertThrows(IllegalArgumentException.class, () -> a.distance(b));
    assertThrows(
        IllegalArgumentException.class,
        () -> new Vector2(WORLD, 1, 0).dot(new Vector2(CAMERA, 1, 0)));
    assertThrows(
        IllegalArgumentException.class,
        () -> WORLD.requireSame(new FrameId(FrameKind.LOCAL_WORLD, "another-session")));
    assertThrows(
        IllegalArgumentException.class,
        () -> new Vector3(new FrameId(FrameKind.IMAGE, "image"), 0, 0, 0));
    assertEquals(WORLD, new FrameId(FrameKind.LOCAL_WORLD, "session"));
    assertEquals(WORLD.hashCode(), new FrameId(FrameKind.LOCAL_WORLD, "session").hashCode());
  }

  @Test
  void knownQuaternionRotationAndInverse() {
    Quaternion q = new Quaternion(1, 0, 0, 1);
    Vector3 x = new Vector3(WORLD, 1, 0, 0);
    xyz(q.rotate(x), 0, 1, 0);
    xyz(q.inverseRotate(q.rotate(x)), 1, 0, 0);
    xyz(q.multiply(q).rotate(x), -1, 0, 0);
    xyz(q.multiply(q.conjugate()).rotate(x), 1, 0, 0);
    assertEquals(1, q.w() * q.w() + q.x() * q.x() + q.y() * q.y() + q.z() * q.z(), TOL);
    assertThrows(IllegalArgumentException.class, () -> new Quaternion(0, 0, 0, 0));
    assertEquals(1, new Quaternion(Double.MAX_VALUE, 0, 0, 0).w());
  }

  @Test
  void transformPointsDirectionsCompositionAndInverse() {
    RigidTransform a =
        new RigidTransform(
            CAMERA, DEVICE, new Quaternion(1, 0, 0, 1), new Vector3(DEVICE, 1, 2, 3));
    RigidTransform b =
        new RigidTransform(DEVICE, WORLD, new Quaternion(1, 1, 0, 0), new Vector3(WORLD, 0, 4, 0));
    Vector3 p = new Vector3(CAMERA, 1, 0, 0);
    xyz(a.transformPoint(p), 1, 3, 3);
    xyz(a.transformDirection(p), 0, 1, 0);
    xyz(a.then(b).transformPoint(p), 1, 1, 3);
    Vector3 round = a.then(b).inverse().transformPoint(a.then(b).transformPoint(p));
    xyz(round, 1, 0, 0);
    assertEquals(CAMERA, round.frame());
    assertThrows(IllegalArgumentException.class, () -> b.then(a));
    assertThrows(
        IllegalArgumentException.class, () -> a.transformPoint(new Vector3(WORLD, 1, 2, 3)));
    assertThrows(
        IllegalArgumentException.class,
        () ->
            new RigidTransform(CAMERA, DEVICE, Quaternion.identity(), new Vector3(WORLD, 0, 0, 0)));
  }

  @Test
  void seededMathematicalInvariants() {
    Random random = new Random(2402);
    RigidTransform t =
        new RigidTransform(
            WORLD, CAMERA, new Quaternion(1, 2, 3, 4), new Vector3(CAMERA, 4, -8, 2));
    for (int i = 0; i < 200; i++) {
      Vector3 a =
          new Vector3(
              WORLD,
              random.nextDouble() * 10 + 1,
              random.nextDouble() * 10,
              random.nextDouble() * 10);
      Vector3 b =
          new Vector3(
              WORLD, random.nextDouble() * 10, random.nextDouble() * 10, random.nextDouble() * 10);
      assertEquals(a.distance(b), b.distance(a), TOL);
      assertEquals(1, a.normalized().magnitude(), TOL);
      assertEquals(a.dot(a), a.magnitude() * a.magnitude(), TOL);
      xyz(a.cross(b).add(b.cross(a)), 0, 0, 0);
      xyz(t.inverse().transformPoint(t.transformPoint(a)), a.x(), a.y(), a.z());
      Vector2 c = new Vector2(WORLD, a.x(), a.y()), d = new Vector2(WORLD, b.x(), b.y());
      assertEquals(c.distance(d), d.distance(c), TOL);
      assertEquals(1, c.normalized().magnitude(), TOL);
      assertEquals(c.dot(c), c.magnitude() * c.magnitude(), TOL);
    }
  }
}
