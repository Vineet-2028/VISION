package dev.sentinel.guardian;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

class CorridorGeometryTest {
  private final FrameId frame = new FrameId(FrameKind.CAMERA, "camera");

  private Vector3 v(double x, double y, double z) {
    return new Vector3(frame, x, y, z);
  }

  @Test
  void rectangleCoordinatesAndSignedDistance() {
    CorridorGeometry.Corridor corridor =
        CorridorGeometry.onPlane(v(0, 0, 0), v(0, 0, 1), v(0, 1, 0), v(0, -1, 0), 1, 5, 1, 1);
    assertArrayEquals(new double[] {0, 3, -1}, corridor.locate(v(0, 1, 3)), 1e-9);
    assertArrayEquals(new double[] {1, 3, 0}, corridor.locate(v(1, 1, 3)), 1e-9);
    assertArrayEquals(new double[] {-2, 3, 1}, corridor.locate(v(-2, 1, 3)), 1e-9);
    assertArrayEquals(new double[] {0, 0, 1}, corridor.locate(v(0, 1, 0)), 1e-9);
    assertArrayEquals(new double[] {0, 6, 1}, corridor.locate(v(0, 1, 6)), 1e-9);
    assertEquals(4, corridor.polygon().size());
  }

  @Test
  void taperRotationAndPlaneProjection() {
    CorridorGeometry.Corridor corridor =
        CorridorGeometry.onPlane(v(2, 0, 3), v(1, 0, 0), v(0, 1, 0), v(0, -1, 0), 1, 5, 1, 2);
    assertArrayEquals(new double[] {1.5, 3, 0}, corridor.locate(v(5, 1, 1.5)), 1e-9);
    assertEquals(1, corridor.origin().y(), 1e-9);
    assertEquals(-1, corridor.right().z(), 1e-9);
  }

  @Test
  void rejectsDegenerateHeadingAndCrossFramePoint() {
    assertThrows(
        IllegalArgumentException.class,
        () ->
            CorridorGeometry.onPlane(v(0, 0, 0), v(0, 1, 0), v(0, 1, 0), v(0, -1, 0), 1, 5, 1, 1));
    CorridorGeometry.Corridor corridor =
        CorridorGeometry.onPlane(v(0, 0, 0), v(0, 0, 1), v(0, 1, 0), v(0, -1, 0), 1, 5, 1, 1);
    assertThrows(
        IllegalArgumentException.class,
        () -> corridor.locate(new Vector3(new FrameId(FrameKind.LOCAL_WORLD, "other"), 0, 1, 3)));
    assertThrows(
        IllegalArgumentException.class,
        () -> new CorridorGeometry.Corridor(v(0, 0, 0), v(0, 0, 1), v(1, 0, 0), 5, 1, 1, 1));
  }
}
