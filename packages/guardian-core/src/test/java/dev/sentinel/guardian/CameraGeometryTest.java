package dev.sentinel.guardian;

import static dev.sentinel.guardian.GeometryFixtures.*;
import static org.junit.jupiter.api.Assertions.*;

import java.util.Optional;
import java.util.OptionalDouble;
import java.util.OptionalLong;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

class CameraGeometryTest {
  @ParameterizedTest
  @ValueSource(doubles = {0, -1, Double.NaN, Double.POSITIVE_INFINITY})
  void invalidFocalLengths(double focal) {
    assertThrows(
        IllegalArgumentException.class,
        () -> new CameraIntrinsics(C, I, 1000, 1000, focal, 1000, 500, 500));
    assertThrows(
        IllegalArgumentException.class,
        () -> new CameraIntrinsics(C, I, 1000, 1000, 1000, focal, 500, 500));
  }

  @Test
  void intrinsicsValidationAndAsymmetricFov() {
    assertThrows(
        IllegalArgumentException.class, () -> new CameraIntrinsics(C, I, 0, 1, 1, 1, 0, 0));
    assertThrows(
        IllegalArgumentException.class,
        () -> CameraIntrinsics.withSkew(C, I, 1, 1, 1, 1, 0, 0, .01));
    CameraIntrinsics k = new CameraIntrinsics(C, I, 1000, 600, 500, 300, 250, 100);
    assertEquals(-StrictMath.atan(.5), k.leftAngleRadians(), 1e-12);
    assertEquals(StrictMath.atan(1.5), k.rightAngleRadians(), 1e-12);
    assertEquals(StrictMath.atan(1.0 / 3), k.topAngleRadians(), 1e-12);
    assertEquals(-StrictMath.atan(5.0 / 3), k.bottomAngleRadians(), 1e-12);
    assertEquals(StrictMath.atan(.5) + StrictMath.atan(1.5), k.horizontalFovRadians(), 1e-12);
    assertEquals(
        StrictMath.atan(1.0 / 3) + StrictMath.atan(5.0 / 3), k.verticalFovRadians(), 1e-12);
    CameraIntrinsics outside = new CameraIntrinsics(C, I, 100, 100, 100, 100, -10, 120);
    assertTrue(outside.leftAngleRadians() > 0);
    assertTrue(outside.horizontalFovRadians() > 0);
    assertEquals(2 * StrictMath.atan(.5), intrinsics().horizontalFovRadians(), 1e-12);
  }

  @ParameterizedTest
  @CsvSource({
    "500,500,0,0,1",
    "1500,500,1,0,1",
    "500,1500,0,1,1",
    "-500,500,-1,0,1",
    "0,0,-0.5,-0.5,1",
    "1000,1000,.5,.5,1"
  })
  void analyticalPixelRays(double u, double v, double x, double y, double z) {
    Vector3 actual = model().pixelToCameraRay(pixel(u, v), frame()).get();
    double n = StrictMath.sqrt(x * x + y * y + z * z);
    MathTest.xyz(actual, x / n, y / n, z / n);
    assertEquals(C, actual.frame());
    assertEquals(1, actual.magnitude(), 1e-12);
  }

  @Test
  void nonSquareFocalsOffCenter() {
    CameraIntrinsics k = new CameraIntrinsics(C, I, 1000, 600, 500, 250, 200, 100);
    Vector3 ray = model(k, new NoDistortion()).pixelToCameraRay(pixel(700, 350), frame(k)).get();
    MathTest.xyz(ray, 1 / StrictMath.sqrt(3), 1 / StrictMath.sqrt(3), 1 / StrictMath.sqrt(3));
  }

  @ParameterizedTest
  @CsvSource({
    "0,0,2,500,500",
    "2,0,2,1500,500",
    "-2,0,2,-500,500",
    "0,2,2,500,1500",
    "0,-2,2,500,-500"
  })
  void analyticalProjection(double x, double y, double z, double u, double v) {
    ProjectionResult result = model().cameraPointToPixel(camera(x, y, z));
    assertTrue(result.isValid());
    assertEquals(u, result.pixel().get().u(), 1e-10);
    assertEquals(v, result.pixel().get().v(), 1e-10);
    assertEquals(u >= 0 && u < 1000 && v >= 0 && v < 1000, result.insideImage());
  }

  @ParameterizedTest
  @ValueSource(doubles = {-1, 0, 1e-12, 1e-6})
  void projectionNearOrBehindIsUnavailable(double z) {
    assertFalse(model().cameraPointToPixel(camera(0, 0, z)).isValid());
  }

  @Test
  void visibilityIsHalfOpenAndNearPlaneConfigurable() {
    CameraFrustum frustum = new CameraFrustum(model());
    assertTrue(frustum.containsCameraPoint(camera(0, 0, 1)));
    assertTrue(frustum.containsCameraPoint(camera(-.5, 0, 1)));
    assertFalse(frustum.containsCameraPoint(camera(.5, 0, 1)));
    assertFalse(frustum.containsCameraPoint(camera(0, .5, 1)));
    CameraModel near =
        new CameraModel(model().calibration(), new GeometryPolicy(.1, 1e-12, 30, 1e-10));
    assertFalse(near.cameraPointToPixel(camera(0, 0, .1)).isValid());
  }

  @Test
  void pointPixelRayRoundtrips() {
    CameraModel camera =
        model(new CameraIntrinsics(C, I, 1000, 600, 780, 590, 330, 260), new NoDistortion());
    for (int x = -5; x <= 5; x++)
      for (int y = -3; y <= 3; y++) {
        Vector3 point = camera(x * .2, y * .3, 2.5);
        PixelPoint p = camera.cameraPointToPixel(point).pixel().get();
        Vector3 ray = camera.pixelToCameraRay(p, frame(camera.calibration().intrinsics())).get();
        assertEquals(0, ray.distance(point.normalized()), 1e-10);
      }
  }

  @ParameterizedTest
  @CsvSource({
    "500,500,0,0",
    "1500,500,.7853981633974483,0",
    "-500,500,-.7853981633974483,0",
    "500,-500,0,.7853981633974483",
    "500,1500,0,-.7853981633974483"
  })
  void analyticalBearings(double u, double v, double horizontal, double vertical) {
    DirectionAngles angles = model().bearing(pixel(u, v), frame()).get();
    assertEquals(horizontal, angles.azimuthRadians(), 1e-10);
    assertEquals(vertical, angles.elevationRadians(), 1e-10);
  }

  @Test
  void distortionAwareBearing() {
    BrownConradyDistortion distortion = new BrownConradyDistortion(.1, 0, 0, 0, 0, 2);
    CameraModel model = model(intrinsics(), distortion);
    // Ideal x=1 distorts to 1.1, so u=1600 still has pi/4 bearing.
    assertEquals(
        StrictMath.PI / 4, model.bearing(pixel(1600, 500), frame()).get().azimuthRadians(), 1e-9);
  }

  @Test
  void calibrationMismatchAndUnboundFramesFailLoudly() {
    assertThrows(
        IllegalArgumentException.class,
        () -> model().pixelToCameraRay(new PixelPoint(image("other"), 500, 500), frame()));
    assertThrows(
        IllegalArgumentException.class, () -> model().cameraPointToPixel(new Vector3(W, 0, 0, 1)));
    FrameMetadata wrong =
        new FrameMetadata(
            0,
            I,
            TIME,
            Optional.empty(),
            1000,
            1000,
            Optional.of(new CalibrationId("rear", "cal2")));
    assertThrows(
        IllegalArgumentException.class, () -> model().pixelToCameraRay(pixel(500, 500), wrong));
    FrameMetadata size =
        new FrameMetadata(0, I, TIME, Optional.empty(), 999, 1000, Optional.of(ID));
    assertThrows(
        IllegalArgumentException.class, () -> model().pixelToCameraRay(pixel(500, 500), size));
    FrameMetadata unbound = new FrameMetadata(0, I, TIME, Optional.empty(), 1000, 1000);
    assertThrows(
        IllegalArgumentException.class, () -> model().pixelToCameraRay(pixel(500, 500), unbound));
  }

  @Test
  void invalidQualityIsUnavailableAndValidQualityRequiresEvidence() {
    assertThrows(
        IllegalArgumentException.class,
        () ->
            new CalibrationQuality(
                CalibrationQuality.State.VALID,
                OptionalDouble.empty(),
                OptionalLong.empty(),
                Optional.empty()));
    CameraModel invalid =
        new CameraModel(
            new CameraCalibration(
                ID,
                intrinsics(),
                new NoDistortion(),
                new CalibrationQuality(
                    CalibrationQuality.State.INVALID,
                    OptionalDouble.empty(),
                    OptionalLong.empty(),
                    Optional.empty()),
                Optional.empty()),
            POLICY);
    assertFalse(invalid.pixelToCameraRay(pixel(500, 500), frame()).isPresent());
    assertFalse(invalid.cameraPointToPixel(camera(0, 0, 1)).isValid());
  }

  @Test
  void extremeInputsFailWithoutNonfiniteOutputs() {
    CameraIntrinsics tiny =
        new CameraIntrinsics(C, I, 1, 1, Double.MIN_VALUE, Double.MIN_VALUE, 0, 0);
    assertFalse(
        model(tiny, new NoDistortion()).pixelToCameraRay(pixel(1, 1), frame(tiny)).isPresent());
    assertFalse(model().cameraPointToPixel(camera(Double.MAX_VALUE, 0, 2e-6)).isValid());
    assertThrows(IllegalArgumentException.class, () -> pixel(Double.NaN, 0));
    assertThrows(
        IllegalArgumentException.class,
        () -> new CameraIntrinsics(C, I, 1, 1, 1, 1, Double.POSITIVE_INFINITY, 0));
  }

  @Test
  void detectionBottomCenterAndAngularExtent() {
    Detection2D detection =
        new Detection2D(
            "fixture", new Confidence(.9), new BoundingBox2D(.25, .25, .75, .75), frame());
    Vector3 ray = model().groundContactRayCandidate(detection).get();
    assertEquals(.25, ray.y() / ray.z(), 1e-12);
    assertEquals(0, ray.x());
    assertEquals(0, model().detectionBearing(detection).get().azimuthRadians());
    AngularExtent extent =
        model()
            .angularExtent(
                PixelBox.fromNormalized(detection.box(), intrinsics().imageSize()), frame())
            .get();
    assertEquals(-StrictMath.atan(.25), extent.leftRadians(), 1e-10);
    assertEquals(StrictMath.atan(.25), extent.rightRadians(), 1e-10);
    assertEquals(StrictMath.atan2(.25, StrictMath.sqrt(1.0625)), extent.topRadians(), 1e-10);
    assertEquals(-extent.topRadians(), extent.bottomRadians(), 1e-10);
  }

  @ParameterizedTest
  @CsvSource({
    "3.141592653589793,3.141592653589793",
    "-3.141592653589793,3.141592653589793",
    "9.42477796076938,3.141592653589793",
    "-12.566370614359172,0"
  })
  void angularNormalization(double input, double expected) {
    assertEquals(expected, Angles.normalizeRadians(input), 1e-12);
  }

  @Test
  void angularDifferenceAvoidsOverflow() {
    assertEquals(
        .2, Angles.shortestAngularDifference(StrictMath.PI - .1, -StrictMath.PI + .1), 1e-12);
    double a = Angles.normalizeRadians(Double.MAX_VALUE);
    assertTrue(Double.isFinite(a) && a > -StrictMath.PI && a <= StrictMath.PI);
    assertTrue(
        Double.isFinite(Angles.shortestAngularDifference(-Double.MAX_VALUE, Double.MAX_VALUE)));
    assertThrows(IllegalArgumentException.class, () -> Angles.normalizeRadians(Double.NaN));
  }
}
