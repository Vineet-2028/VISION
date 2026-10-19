package dev.sentinel.guardian;

import static dev.sentinel.guardian.GeometryFixtures.*;
import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

class DistortionTest {
  @Test
  void noDistortionAndZeroCoefficients() {
    CameraPlanePoint p = new CameraPlanePoint(C, .2, .3);
    assertSame(p, new NoDistortion().undistort(p, POLICY).get());
    CameraPlanePoint q = new BrownConradyDistortion(0, 0, 0, 0, 0, 2).distort(p).get();
    assertEquals(.2, q.x());
    assertEquals(.3, q.y());
  }

  @Test
  void analyticalRadial() {
    CameraPlanePoint q =
        new BrownConradyDistortion(.1, 0, 0, 0, 0, 2)
            .distort(new CameraPlanePoint(C, .2, .3))
            .get();
    assertEquals(.2026, q.x(), 1e-12);
    assertEquals(.3039, q.y(), 1e-12);
  }

  @Test
  void analyticalTangential() {
    CameraPlanePoint q =
        new BrownConradyDistortion(0, 0, 0, .001, -.002, 2)
            .distort(new CameraPlanePoint(C, .2, .3))
            .get();
    assertEquals(.1997, q.x(), 1e-12);
    assertEquals(.30007, q.y(), 1e-12);
  }

  @ParameterizedTest
  @CsvSource({
    "0,0,0,0,0",
    ".1,.01,.001,0,0",
    "0,0,0,.001,-.002",
    ".5,.05,.005,.002,.001",
    "-.1,0,0,0,0"
  })
  void gridRoundtrip(double k1, double k2, double k3, double p1, double p2) {
    BrownConradyDistortion distortion = new BrownConradyDistortion(k1, k2, k3, p1, p2, 1.5);
    for (int x = -5; x <= 5; x++)
      for (int y = -5; y <= 5; y++) {
        CameraPlanePoint original = new CameraPlanePoint(C, x * .15, y * .15);
        CameraPlanePoint distorted = distortion.distort(original).get();
        CameraPlanePoint restored = distortion.undistort(distorted, POLICY).get();
        assertEquals(original.x(), restored.x(), 1e-8);
        assertEquals(original.y(), restored.y(), 1e-8);
        assertEquals(C, restored.frame());
      }
  }

  @Test
  void boundedNonconvergenceAndInvalidDomain() {
    BrownConradyDistortion strong = new BrownConradyDistortion(.5, 0, 0, 0, 0, 2);
    CameraPlanePoint p = strong.distort(new CameraPlanePoint(C, 1, .7)).get();
    assertFalse(strong.undistort(p, new GeometryPolicy(1e-6, 1e-12, 1, 1e-14)).isPresent());
    assertFalse(strong.distort(new CameraPlanePoint(C, 3, 0)).isPresent());
    assertFalse(strong.undistort(new CameraPlanePoint(C, 10000, 10000), POLICY).isPresent());
    assertThrows(
        IllegalArgumentException.class, () -> new BrownConradyDistortion(-1, 0, 0, 0, 0, 2));
    assertThrows(
        IllegalArgumentException.class,
        () -> new BrownConradyDistortion(Double.NaN, 0, 0, 0, 0, 1));
    assertThrows(IllegalArgumentException.class, () -> new GeometryPolicy(1e-6, 1e-12, 0, 1e-10));
  }
}
