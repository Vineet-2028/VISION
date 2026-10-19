package dev.sentinel.guardian;

import static dev.sentinel.guardian.TemporalFixtures.*;
import static org.junit.jupiter.api.Assertions.*;

import java.util.Optional;
import java.util.OptionalDouble;
import org.junit.jupiter.api.Test;

class StreamingMotionTest {
  private static TimedVectorEstimate position(long t, double x) {
    return estimate(t, VectorEstimate.Quantity.POSITION_METERS, x);
  }

  private static DerivativeEstimator velocity(OptionalDouble cutoff) {
    return new DerivativeEstimator(
        VectorEstimate.Quantity.POSITION_METERS, 1000, 2000000000, 20, cutoff);
  }

  @Test
  void constantVelocityIrregularTimingHasMidpointTime() {
    DerivativeEstimator v = velocity(OptionalDouble.empty());
    assertEquals(DerivativeEstimator.Status.INITIALIZED, v.update(position(0, 0)).status());
    DerivativeEstimator.Result a = v.update(position(1000000000, 2));
    assertEquals(2, a.estimate().get().estimate().value().get().x());
    assertEquals(500000000, a.estimate().get().time().nanos());
    assertEquals(1000000000, a.availableAt().nanos());
    assertEquals(
        2, v.update(position(1500000000, 3)).estimate().get().estimate().value().get().x());
  }

  @Test
  void tooSoonOutlierAndGapDoNotLeakStaleDerivative() {
    DerivativeEstimator v = velocity(OptionalDouble.empty());
    v.update(position(0, 0));
    assertEquals(DerivativeEstimator.Status.TOO_SOON, v.update(position(999, 99)).status());
    assertEquals(DerivativeEstimator.Status.OUTLIER, v.update(position(1000000000, 100)).status());
    assertEquals(
        2, v.update(position(1000000000, 2)).estimate().get().estimate().value().get().x());
    DerivativeEstimator.Result gap = v.update(position(4000000000L, 8));
    assertEquals(DerivativeEstimator.Status.GAP_RESET, gap.status());
    assertFalse(gap.estimate().isPresent());
    assertEquals(
        2, v.update(position(5000000000L, 10)).estimate().get().estimate().value().get().x());
  }

  @Test
  void stationaryResetUnknownAndMismatchedSession() {
    DerivativeEstimator v = velocity(OptionalDouble.empty());
    v.update(position(0, 2));
    assertEquals(
        0, v.update(position(1000000000, 2)).estimate().get().estimate().value().get().x());
    assertThrows(IllegalArgumentException.class, () -> v.update(position(10, 2)));
    assertThrows(
        IllegalArgumentException.class,
        () ->
            v.update(
                new TimedVectorEstimate(
                    new MonotonicTime("other", 2000000000), position(0, 2).estimate())));
    assertThrows(
        IllegalArgumentException.class,
        () ->
            v.update(
                new TimedVectorEstimate(
                    time(2000000000),
                    new VectorEstimate(
                        new FrameId(FrameKind.LOCAL_WORLD, "other"),
                        VectorEstimate.Quantity.POSITION_METERS,
                        Optional.of(
                            new Vector3(new FrameId(FrameKind.LOCAL_WORLD, "other"), 2, 0, 0)),
                        Optional.empty(),
                        new Confidence(1)))));
    TimedVectorEstimate unknown =
        new TimedVectorEstimate(
            time(2000000000),
            new VectorEstimate(
                WORLD,
                VectorEstimate.Quantity.POSITION_METERS,
                Optional.empty(),
                Optional.empty(),
                new Confidence(0)));
    assertEquals(DerivativeEstimator.Status.UNKNOWN_RESET, v.update(unknown).status());
    assertEquals(
        DerivativeEstimator.Status.INITIALIZED, v.update(position(3000000000L, 3)).status());
    v.reset();
    assertEquals(DerivativeEstimator.Status.INITIALIZED, v.update(position(0, 0)).status());
  }

  @Test
  void smoothingReducesAlternatingDerivativeNoise() {
    DerivativeEstimator raw = velocity(OptionalDouble.empty()),
        smooth = velocity(OptionalDouble.of(1 / (2 * StrictMath.PI)));
    raw.update(position(0, 0));
    smooth.update(position(0, 0));
    double rawError = 0, smoothError = 0;
    for (int i = 1; i <= 20; i++) {
      double x = 2 * i + (i % 2 == 0 ? 0 : .5);
      double r =
          raw.update(position(i * 1000000000L, x)).estimate().get().estimate().value().get().x();
      double s =
          smooth.update(position(i * 1000000000L, x)).estimate().get().estimate().value().get().x();
      if (i > 3) {
        rawError += (r - 2) * (r - 2);
        smoothError += (s - 2) * (s - 2);
      }
    }
    assertTrue(smoothError < rawError);
  }

  @Test
  void accelerationFromVelocityAndInvalidDt() {
    DerivativeEstimator a =
        new DerivativeEstimator(
            VectorEstimate.Quantity.VELOCITY_MPS, 1000, 2000000000, 10, OptionalDouble.empty());
    a.update(estimate(0, VectorEstimate.Quantity.VELOCITY_MPS, 1));
    TimedVectorEstimate result =
        a.update(estimate(1000000000, VectorEstimate.Quantity.VELOCITY_MPS, 4)).estimate().get();
    assertEquals(VectorEstimate.Quantity.ACCELERATION_MPS2, result.estimate().quantity());
    assertEquals(3, result.estimate().value().get().x());
    assertEquals(
        DerivativeEstimator.Status.TOO_SOON,
        a.update(estimate(1000000000, VectorEstimate.Quantity.VELOCITY_MPS, 5)).status());
    assertThrows(
        IllegalArgumentException.class,
        () ->
            new DerivativeEstimator(
                VectorEstimate.Quantity.VELOCITY_MPS, 1, 10, 10, OptionalDouble.empty()));
  }

  @Test
  void noisyVelocityFilteredAcceleration() {
    DerivativeEstimator a =
        new DerivativeEstimator(
            VectorEstimate.Quantity.VELOCITY_MPS,
            1000,
            2000000000,
            10,
            OptionalDouble.of(1 / (2 * StrictMath.PI)));
    a.update(estimate(0, VectorEstimate.Quantity.VELOCITY_MPS, 0));
    assertEquals(
        4,
        a.update(estimate(1000000000, VectorEstimate.Quantity.VELOCITY_MPS, 4))
            .estimate()
            .get()
            .estimate()
            .value()
            .get()
            .x());
    assertEquals(
        3,
        a.update(estimate(2000000000, VectorEstimate.Quantity.VELOCITY_MPS, 6))
            .estimate()
            .get()
            .estimate()
            .value()
            .get()
            .x(),
        1e-12);
  }

  @Test
  void explicitPredictionModelsAndHorizon() {
    TimedVectorEstimate p = position(0, 1),
        v = estimate(0, VectorEstimate.Quantity.VELOCITY_MPS, 2),
        a = estimate(0, VectorEstimate.Quantity.ACCELERATION_MPS2, 3);
    assertEquals(
        1,
        MotionPrediction.position(
                MotionPrediction.Model.CONSTANT_POSITION,
                p,
                Optional.empty(),
                Optional.empty(),
                time(2000000000),
                2000000000)
            .get()
            .estimate()
            .value()
            .get()
            .x());
    assertEquals(
        5,
        MotionPrediction.position(
                MotionPrediction.Model.CONSTANT_VELOCITY,
                p,
                Optional.of(v),
                Optional.empty(),
                time(2000000000),
                2000000000)
            .get()
            .estimate()
            .value()
            .get()
            .x());
    assertEquals(
        11,
        MotionPrediction.position(
                MotionPrediction.Model.CONSTANT_ACCELERATION,
                p,
                Optional.of(v),
                Optional.of(a),
                time(2000000000),
                2000000000)
            .get()
            .estimate()
            .value()
            .get()
            .x());
    assertEquals(8, MotionPrediction.velocity(world(2, 0, 0), world(3, 0, 0), 2).x());
    assertFalse(
        MotionPrediction.position(
                MotionPrediction.Model.CONSTANT_VELOCITY,
                p,
                Optional.empty(),
                Optional.empty(),
                time(1),
                10)
            .isPresent());
    assertFalse(
        MotionPrediction.position(
                MotionPrediction.Model.CONSTANT_POSITION,
                p,
                Optional.empty(),
                Optional.empty(),
                time(11),
                10)
            .isPresent());
    assertThrows(
        IllegalArgumentException.class,
        () ->
            MotionPrediction.position(
                MotionPrediction.Model.CONSTANT_VELOCITY,
                p,
                Optional.of(estimate(1, VectorEstimate.Quantity.VELOCITY_MPS, 2)),
                Optional.empty(),
                time(10),
                10));
  }
}
