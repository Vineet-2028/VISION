package dev.sentinel.guardian;

import static org.junit.jupiter.api.Assertions.*;

import java.util.Optional;
import java.util.OptionalDouble;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

class ContractsTest {
  private static final FrameId W = new FrameId(FrameKind.LOCAL_WORLD, "session");
  private static final FrameId I = new FrameId(FrameKind.IMAGE, "camera:uncropped");
  private static final FrameId C = new FrameId(FrameKind.CAMERA, "rear");
  private static final MonotonicTime TIME = new MonotonicTime("sensor", 42);
  private static final Confidence SCORE = new Confidence(.8);

  private static VectorEstimate unknown(VectorEstimate.Quantity quantity) {
    return new VectorEstimate(W, quantity, Optional.empty(), Optional.empty(), new Confidence(0));
  }

  @ParameterizedTest
  @ValueSource(
      doubles = {-1, 1.001, Double.NaN, Double.POSITIVE_INFINITY, Double.NEGATIVE_INFINITY})
  void invalidConfidence(double value) {
    assertThrows(IllegalArgumentException.class, () -> new Confidence(value));
  }

  @ParameterizedTest
  @ValueSource(doubles = {0, .1, .5, .99, 1})
  void confidenceBounds(double value) {
    assertEquals(value, new Confidence(value).value());
  }

  @Test
  void knownAndUnknownScalarUncertainty() {
    ScalarEstimate known = ScalarEstimate.known(-2, OptionalDouble.of(.3), SCORE);
    assertEquals(Validity.KNOWN, known.validity());
    assertEquals(-2, known.value().getAsDouble());
    assertEquals(.3, known.standardDeviation().getAsDouble());
    assertEquals(.8, known.confidence().value());
    ScalarEstimate unknown = ScalarEstimate.unknown();
    assertEquals(Validity.UNKNOWN, unknown.validity());
    assertFalse(unknown.value().isPresent());
    assertFalse(unknown.standardDeviation().isPresent());
    assertThrows(
        IllegalArgumentException.class,
        () -> ScalarEstimate.known(1, OptionalDouble.of(-1), SCORE));
    assertThrows(
        IllegalArgumentException.class,
        () -> ScalarEstimate.known(Double.NaN, OptionalDouble.empty(), SCORE));
    assertThrows(
        IllegalArgumentException.class,
        () -> ScalarEstimate.known(1, OptionalDouble.of(Double.NaN), SCORE));
  }

  @Test
  void relativeDepthCannotMasqueradeAsMeters() {
    DepthEstimate relative =
        DepthEstimate.relative(-2, OptionalDouble.empty(), SCORE, "model:inverse-order");
    assertFalse(relative.meters().isPresent());
    assertEquals(-2, relative.estimate().value().getAsDouble());
    DepthEstimate metric = DepthEstimate.metricRange(3, OptionalDouble.of(.5), SCORE, "stereo");
    assertEquals(3, metric.meters().getAsDouble());
    DepthEstimate unknown = DepthEstimate.unknown(DepthEstimate.Scale.METRIC_RANGE, "unavailable");
    assertFalse(unknown.meters().isPresent());
    assertEquals(Validity.UNKNOWN, unknown.estimate().validity());
    assertThrows(
        IllegalArgumentException.class,
        () -> DepthEstimate.metricRange(0, OptionalDouble.empty(), SCORE, "sensor"));
    assertThrows(
        IllegalArgumentException.class,
        () -> DepthEstimate.metricRange(-1, OptionalDouble.empty(), SCORE, "sensor"));
    assertThrows(
        IllegalArgumentException.class,
        () -> DepthEstimate.relative(1, OptionalDouble.empty(), SCORE, " "));
  }

  @Test
  void imageContractsPreserveSourceAndTime() {
    FrameMetadata frame =
        new FrameMetadata(7, I, TIME, Optional.of(new WallClockTime(1700000000000L)), 640, 480);
    Detection2D detection =
        new Detection2D("detector:pedestrian", SCORE, new BoundingBox2D(0, .1, 1, .9), frame);
    assertSame(frame, detection.frame());
    assertSame(TIME, detection.frame().captureTime());
    assertEquals(7, detection.frame().sequence());
    assertEquals(640, frame.widthPixels());
    assertEquals(480, frame.heightPixels());
    assertEquals(1700000000000L, frame.wallClockTime().get().epochMillis());
    CameraIntrinsics intrinsics = new CameraIntrinsics(C, I, 640, 480, 500, 501, 320, 240);
    assertEquals(500, intrinsics.fxPixels());
    assertEquals(501, intrinsics.fyPixels());
    assertEquals(320, intrinsics.cxPixels());
    assertEquals(240, intrinsics.cyPixels());
    assertThrows(
        IllegalArgumentException.class,
        () -> new FrameMetadata(-1, I, TIME, Optional.empty(), 1, 1));
    assertThrows(
        IllegalArgumentException.class,
        () -> new FrameMetadata(0, I, TIME, Optional.empty(), 0, 1));
    assertThrows(
        IllegalArgumentException.class,
        () -> new FrameMetadata(0, C, TIME, Optional.empty(), 1, 1));
    assertThrows(
        IllegalArgumentException.class,
        () -> new CameraIntrinsics(C, I, 640, 480, 0, 500, 320, 240));
    assertThrows(
        IllegalArgumentException.class, () -> new Detection2D("", SCORE, detection.box(), frame));
  }

  @Test
  void boxesRejectInvalidBoundsAndArea() {
    assertThrows(IllegalArgumentException.class, () -> new BoundingBox2D(-.1, 0, 1, 1));
    assertThrows(IllegalArgumentException.class, () -> new BoundingBox2D(0, 0, 1.1, 1));
    assertThrows(IllegalArgumentException.class, () -> new BoundingBox2D(.5, 0, .5, 1));
    assertThrows(IllegalArgumentException.class, () -> new BoundingBox2D(0, .7, 1, .6));
    assertThrows(IllegalArgumentException.class, () -> new BoundingBox2D(0, 0, Double.NaN, 1));
  }

  @Test
  void inertialContractsHaveDistinctGravitySemantics() {
    Vector3 gravity = new Vector3(W, 0, 0, 9.81), zero = new Vector3(W, 0, 0, 0);
    ImuSample raw = new ImuSample(TIME, gravity, zero);
    LinearAccelerationSample linear = new LinearAccelerationSample(TIME, zero);
    AngularVelocitySample gyro = new AngularVelocitySample(TIME, new Vector3(W, 0, 0, 2));
    assertEquals(9.81, raw.rawSpecificForceMps2().z());
    assertEquals(0, linear.metersPerSecondSquared().z());
    assertEquals(2, gyro.radiansPerSecond().z());
    assertSame(TIME, raw.time());
    assertThrows(
        IllegalArgumentException.class,
        () -> new ImuSample(TIME, gravity, new Vector3(C, 0, 0, 0)));
  }

  @Test
  void orientationUnknownAndFrameValidation() {
    OrientationEstimate orientation =
        new OrientationEstimate(
            C, W, TIME, Optional.of(Quaternion.identity()), OptionalDouble.of(.1), SCORE);
    assertEquals(.1, orientation.standardDeviationRadians().getAsDouble());
    OrientationEstimate unknown =
        new OrientationEstimate(
            C, W, TIME, Optional.empty(), OptionalDouble.empty(), new Confidence(0));
    assertFalse(unknown.rotation().isPresent());
    assertThrows(
        IllegalArgumentException.class,
        () ->
            new OrientationEstimate(
                I, W, TIME, Optional.empty(), OptionalDouble.empty(), new Confidence(0)));
    assertThrows(
        IllegalArgumentException.class,
        () ->
            new OrientationEstimate(
                C, W, TIME, Optional.empty(), OptionalDouble.of(.1), new Confidence(0)));
    assertThrows(
        IllegalArgumentException.class,
        () -> new OrientationEstimate(C, W, TIME, Optional.empty(), OptionalDouble.empty(), SCORE));
  }

  @Test
  void trackedEntityIsASnapshotWithExplicitUnknowns() {
    VectorEstimate position =
        new VectorEstimate(
            W,
            VectorEstimate.Quantity.POSITION_METERS,
            Optional.of(new Vector3(W, 1, 2, 3)),
            Optional.of(new Vector3(W, .1, .2, .3)),
            SCORE);
    VectorEstimate velocity = unknown(VectorEstimate.Quantity.VELOCITY_MPS),
        acceleration = unknown(VectorEstimate.Quantity.ACCELERATION_MPS2);
    TrackedEntity entity =
        new TrackedEntity(
            "session:track1",
            "detector:pedestrian",
            TIME,
            position,
            velocity,
            acceleration,
            SCORE,
            TrackedEntity.Lifecycle.TENTATIVE,
            1);
    assertSame(position, entity.position());
    assertFalse(entity.velocity().value().isPresent());
    assertFalse(entity.acceleration().value().isPresent());
    assertEquals(1, entity.observationCount());
    assertEquals(TrackedEntity.Lifecycle.TENTATIVE, entity.lifecycle());
    assertThrows(
        IllegalArgumentException.class,
        () ->
            new TrackedEntity(
                "id",
                "category",
                TIME,
                velocity,
                position,
                acceleration,
                SCORE,
                TrackedEntity.Lifecycle.LOST,
                1));
    assertThrows(
        IllegalArgumentException.class,
        () ->
            new TrackedEntity(
                "id",
                "category",
                TIME,
                position,
                velocity,
                acceleration,
                SCORE,
                TrackedEntity.Lifecycle.LOST,
                0));
    assertThrows(
        IllegalArgumentException.class,
        () ->
            new VectorEstimate(
                W,
                VectorEstimate.Quantity.POSITION_METERS,
                Optional.of(new Vector3(C, 1, 2, 3)),
                Optional.empty(),
                SCORE));
    assertThrows(
        IllegalArgumentException.class,
        () ->
            new VectorEstimate(
                W,
                VectorEstimate.Quantity.POSITION_METERS,
                Optional.of(new Vector3(W, 1, 2, 3)),
                Optional.of(new Vector3(W, -1, 0, 0)),
                SCORE));
    assertThrows(
        IllegalArgumentException.class,
        () ->
            new VectorEstimate(
                W,
                VectorEstimate.Quantity.POSITION_METERS,
                Optional.empty(),
                Optional.empty(),
                SCORE));
  }
}
