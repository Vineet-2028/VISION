package dev.sentinel.guardian;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

class ImageRollTest {
  private final FrameId source = new FrameId(FrameKind.IMAGE, "source");
  private final FrameId target = new FrameId(FrameKind.IMAGE, "roll");

  @Test
  void expandedAndPaddedCanvasesContainEveryOriginalCornerAndInvert() {
    ImageSize size = new ImageSize(source, 1906, 876);
    for (String canvas : new String[] {"EXPAND", "PAD"}) {
      for (int degrees : new int[] {-60, -45, -30, -20, -15, -10, 0, 10, 15, 20, 30, 45, 60}) {
        ImageTransform transform =
            ImageTransform.roll(size, target, StrictMath.toRadians(degrees), canvas);
        for (double x : new double[] {0, size.width()}) {
          for (double y : new double[] {0, size.height()}) {
            PixelPoint mapped = transform.forward(new PixelPoint(source, x, y));
            assertTrue(mapped.u() >= -1e-9 && mapped.u() <= transform.to().width() + 1e-9);
            assertTrue(mapped.v() >= -1e-9 && mapped.v() <= transform.to().height() + 1e-9);
            PixelPoint restored = transform.inverse().forward(mapped);
            assertEquals(x, restored.u(), 1e-9);
            assertEquals(y, restored.v(), 1e-9);
          }
        }
      }
    }
  }

  @Test
  void cropPreservesCanvasAndRotationPreservesCenter() {
    ImageSize size = new ImageSize(source, 640, 480);
    ImageTransform transform = ImageTransform.roll(size, target, 0.4, "CROP");
    assertEquals(640, transform.to().width());
    assertEquals(480, transform.to().height());
    PixelPoint center = transform.forward(new PixelPoint(source, 320, 240));
    assertEquals(320, center.u(), 1e-9);
    assertEquals(240, center.v(), 1e-9);
    assertTrue(transform.forward(new PixelPoint(source, 0, 0)).v() < 0);
    assertThrows(
        IllegalArgumentException.class, () -> ImageTransform.roll(size, target, Double.NaN, "PAD"));
    assertThrows(IllegalArgumentException.class, () -> ImageTransform.roll(size, target, 4, "PAD"));
    assertThrows(
        IllegalArgumentException.class, () -> ImageTransform.roll(size, target, 0, "OTHER"));
  }
}
