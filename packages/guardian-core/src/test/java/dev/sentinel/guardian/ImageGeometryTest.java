package dev.sentinel.guardian;

import static dev.sentinel.guardian.GeometryFixtures.*;
import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

class ImageGeometryTest {
  private static void pixelEquals(PixelPoint actual, double u, double v) {
    assertEquals(u, actual.u(), 1e-9);
    assertEquals(v, actual.v(), 1e-9);
  }

  @Test
  void normalizedPixelBoxesAndRawOutliers() {
    ImageSize size = new ImageSize(I, 640, 480);
    PixelBox b = PixelBox.fromNormalized(new BoundingBox2D(.25, .25, .75, .75), size);
    assertEquals(320, b.width());
    assertEquals(240, b.height());
    pixelEquals(b.center(), 320, 240);
    pixelEquals(b.bottomCenter(), 320, 360);
    assertEquals(.25, b.toNormalized(size).minX());
    PixelBox raw = new PixelBox(I, -20, -10, 700, 500);
    assertEquals(-20, raw.minU());
    assertEquals(700, raw.maxU());
    PixelBox clipped = raw.clamp(size);
    assertEquals(0, clipped.minU());
    assertEquals(640, clipped.maxU());
    assertEquals(480, clipped.maxV());
    assertThrows(IllegalArgumentException.class, () -> raw.toNormalized(size));
    PixelBox empty = new PixelBox(I, 2, 2, 2, 2);
    assertEquals(0, empty.width());
    assertEquals(0, empty.height());
    assertThrows(IllegalArgumentException.class, () -> empty.toNormalized(size));
    PixelBox outside = new PixelBox(I, 700, 500, 800, 600).clamp(size);
    assertEquals(0, outside.width());
    assertEquals(0, outside.height());
    assertThrows(IllegalArgumentException.class, () -> new PixelBox(I, 2, 0, 1, 2));
    assertThrows(IllegalArgumentException.class, () -> new PixelBox(I, 0, 0, Double.NaN, 1));
  }

  @Test
  void normalizedPointsAreNotCameraPlaneCoordinates() {
    ImageSize size = new ImageSize(I, 640, 480);
    pixelEquals(new NormalizedImagePoint(I, .5, .25).toPixels(size), 320, 120);
    assertEquals(.5, NormalizedImagePoint.fromPixels(pixel(320, 120), size).x());
    assertThrows(IllegalArgumentException.class, () -> new NormalizedImagePoint(I, 1.1, 0));
    CameraPlanePoint unbounded = new CameraPlanePoint(C, 2, -3);
    assertEquals(2, unbounded.x());
  }

  @Test
  void knownScaleAndCropIntrinsics() {
    CameraIntrinsics original = new CameraIntrinsics(C, I, 1000, 600, 800, 400, 300, 200);
    ImageSize target = new ImageSize(image("scaled"), 500, 150);
    CameraIntrinsics scaled = original.scaledTo(target);
    assertEquals(400, scaled.fxPixels());
    assertEquals(100, scaled.fyPixels());
    assertEquals(150, scaled.cxPixels());
    assertEquals(50, scaled.cyPixels());
    pixelEquals(
        ImageTransform.scale(original.imageSize(), target).forward(pixel(300, 200)), 150, 50);
    ImageSize crop = new ImageSize(image("crop"), 400, 300);
    CameraIntrinsics cropped = original.croppedTo(crop, 200, 100);
    assertEquals(100, cropped.cxPixels());
    assertEquals(100, cropped.cyPixels());
    assertEquals(800, cropped.fxPixels());
    pixelEquals(
        ImageTransform.crop(original.imageSize(), crop, 200, 100).forward(pixel(300, 200)),
        100,
        100);
    assertThrows(IllegalArgumentException.class, () -> original.croppedTo(crop, 700, 100));
    assertThrows(
        IllegalArgumentException.class,
        () -> ImageTransform.crop(original.imageSize(), crop, -1, 0));
  }

  @ParameterizedTest
  @CsvSource({
    "0,640,480,100,50,80,60,500,400",
    "1,480,640,430,100,420,80,400,500",
    "2,640,480,540,430,560,420,500,400",
    "3,480,640,50,540,60,560,400,500"
  })
  void quarterTurnPixelAndIntrinsics(
      int turns,
      int width,
      int height,
      double u,
      double v,
      double cx,
      double cy,
      double fx,
      double fy) {
    CameraIntrinsics original = new CameraIntrinsics(C, I, 640, 480, 500, 400, 80, 60);
    RotatedIntrinsics rotated =
        new RotatedIntrinsics(
            original,
            image("rot" + turns),
            new FrameId(FrameKind.CAMERA, "rotated" + turns),
            turns);
    assertEquals(width, rotated.intrinsics().widthPixels());
    assertEquals(height, rotated.intrinsics().heightPixels());
    pixelEquals(rotated.imageTransform().forward(pixel(100, 50)), u, v);
    assertEquals(cx, rotated.intrinsics().cxPixels());
    assertEquals(cy, rotated.intrinsics().cyPixels());
    assertEquals(fx, rotated.intrinsics().fxPixels());
    assertEquals(fy, rotated.intrinsics().fyPixels());
    pixelEquals(
        rotated.imageTransform().inverse().forward(rotated.imageTransform().forward(pixel(.5, .5))),
        .5,
        .5);
    // Independent projection after the required optical basis rotation must match image rotation.
    Vector3 p = camera(.2, .1, 2);
    Vector3 r = rotated.originalCameraToRotatedCamera().transformPoint(p);
    PixelPoint originalProjection = new PixelPoint(I, 500 * .2 / 2 + 80, 400 * .1 / 2 + 60);
    PixelPoint expected = rotated.imageTransform().forward(originalProjection);
    assertEquals(expected.u(), fx * r.x() / r.z() + cx, 1e-9);
    assertEquals(expected.v(), fy * r.y() / r.z() + cy, 1e-9);
    PixelBox b = rotated.imageTransform().forward(new PixelBox(I, 10, 20, 30, 50));
    assertEquals(turns % 2 == 0 ? 20 : 30, b.width(), 1e-9);
    assertEquals(turns % 2 == 0 ? 30 : 20, b.height(), 1e-9);
  }

  @Test
  void continuousPixelCentersAvoidOffByOne() {
    ImageTransform t = ImageTransform.rotateClockwise(new ImageSize(I, 640, 480), image("r"), 1);
    pixelEquals(t.forward(pixel(.5, .5)), 479.5, .5);
    pixelEquals(t.forward(pixel(0, 0)), 480, 0);
    pixelEquals(t.forward(pixel(640, 480)), 0, 640);
  }

  @ParameterizedTest
  @CsvSource({
    "640,640,320,320,320,320,160,160",
    "640,480,640,640,0,0,0,80",
    "480,640,640,640,0,0,80,0",
    "5,2,8,8,0,0,0,2.4"
  })
  void exactLetterbox(
      int sw, int sh, int tw, int th, double u, double v, double expectedU, double expectedV) {
    ImageTransform t =
        ImageTransform.letterbox(new ImageSize(I, sw, sh), new ImageSize(image("model"), tw, th));
    pixelEquals(t.forward(pixel(u, v)), expectedU, expectedV);
    for (double x : new double[] {-.5, .5, sw / 2.0, sw})
      for (double y : new double[] {0, .5, sh}) {
        pixelEquals(t.inverse().forward(t.forward(pixel(x, y))), x, y);
      }
    PixelBox original = new PixelBox(I, 0, 0, sw, sh);
    PixelBox recovered = t.inverse().forward(t.forward(original));
    assertEquals(0, recovered.minU(), 1e-9);
    assertEquals(sw, recovered.maxU(), 1e-9);
    assertEquals(sh, recovered.maxV(), 1e-9);
  }

  @Test
  void explicitOddIntegerPaddingAndComposition() {
    ImageSize source = new ImageSize(I, 5, 3),
        scaled = new ImageSize(image("scaled"), 10, 6),
        padded = new ImageSize(image("padded"), 15, 11);
    ImageTransform pipeline =
        ImageTransform.scale(source, scaled).then(ImageTransform.pad(scaled, padded, 2, 3));
    pixelEquals(pipeline.forward(pixel(1, 1)), 4, 5);
    pixelEquals(pipeline.inverse().forward(pipeline.forward(pixel(1, 1))), 1, 1);
    assertThrows(
        IllegalArgumentException.class, () -> pipeline.then(ImageTransform.scale(source, scaled)));
    assertThrows(IllegalArgumentException.class, () -> ImageTransform.pad(scaled, padded, 6, 0));
    assertThrows(
        IllegalArgumentException.class,
        () -> ImageTransform.rotateClockwise(source, image("bad"), 4));
  }

  @Test
  void hugeDimensionsUseFloatingRatiosWithoutIntegerOverflow() {
    ImageSize from = new ImageSize(I, Integer.MAX_VALUE, Integer.MAX_VALUE),
        to = new ImageSize(image("small"), 1, 1);
    pixelEquals(
        ImageTransform.scale(from, to).forward(pixel(Integer.MAX_VALUE, Integer.MAX_VALUE)), 1, 1);
    assertThrows(
        IllegalArgumentException.class,
        () -> ImageTransform.crop(from, new ImageSize(image("crop"), 2, 2), Integer.MAX_VALUE, 0));
  }

  @Test
  void transformedGeometryCannotReuseSourceIdentity() {
    ImageSize source = new ImageSize(I, 1000, 1000);
    ImageSize smaller = new ImageSize(I, 500, 500);
    assertThrows(IllegalArgumentException.class, () -> ImageTransform.scale(source, smaller));
    assertThrows(
        IllegalArgumentException.class, () -> ImageTransform.crop(source, smaller, 20, 30));
    assertThrows(IllegalArgumentException.class, () -> ImageTransform.pad(smaller, source, 20, 30));
    assertThrows(IllegalArgumentException.class, () -> ImageTransform.letterbox(source, smaller));
    assertThrows(
        IllegalArgumentException.class, () -> ImageTransform.rotateClockwise(source, I, 1));
    assertThrows(IllegalArgumentException.class, () -> intrinsics().scaledTo(smaller));
    assertThrows(IllegalArgumentException.class, () -> intrinsics().croppedTo(smaller, 20, 30));
    assertThrows(
        IllegalArgumentException.class,
        () -> new RotatedIntrinsics(intrinsics(), I, new FrameId(FrameKind.CAMERA, "rotated"), 1));
  }

  @Test
  void compositionWithInverseCanReturnToOriginalIdentity() {
    ImageTransform forward =
        ImageTransform.rotateClockwise(new ImageSize(I, 1000, 1000), image("rotated"), 1);
    ImageTransform identity = forward.then(forward.inverse());
    PixelPoint recovered = identity.forward(pixel(42.5, 19.5));
    assertEquals(I, recovered.frame());
    pixelEquals(recovered, 42.5, 19.5);
  }
}
