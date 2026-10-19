package dev.sentinel.guardian;

import java.util.Optional;

/** Explicit nominal kinematic prediction. No uncertainty bound or object tracking is implied. */
public final class MotionPrediction {
  public enum Model {
    CONSTANT_POSITION,
    CONSTANT_VELOCITY,
    CONSTANT_ACCELERATION
  }

  private MotionPrediction() {}

  public static Optional<TimedVectorEstimate> position(
      Model model,
      TimedVectorEstimate position,
      Optional<TimedVectorEstimate> velocity,
      Optional<TimedVectorEstimate> acceleration,
      MonotonicTime target,
      long maxHorizonNanos) {
    if (model == null) throw new IllegalArgumentException("Missing motion model");
    if (maxHorizonNanos < 0) throw new IllegalArgumentException("Negative prediction horizon");
    if (position.estimate().quantity() != VectorEstimate.Quantity.POSITION_METERS
        || position.estimate().frame().kind() != FrameKind.LOCAL_WORLD)
      throw new IllegalArgumentException("WORLD position required");
    long nanos = target.elapsedNanosSince(position.time());
    if (nanos > maxHorizonNanos || !position.estimate().value().isPresent())
      return Optional.empty();
    double dt = nanos / 1_000_000_000.0;
    Vector3 p = position.estimate().value().get();
    double confidence = position.estimate().confidence().value();
    if (model != Model.CONSTANT_POSITION) {
      if (!velocity.isPresent()) return Optional.empty();
      requireCompatible(position, velocity.get(), VectorEstimate.Quantity.VELOCITY_MPS);
      if (!velocity.get().estimate().value().isPresent()) return Optional.empty();
      p = p.add(velocity.get().estimate().value().get().multiply(dt));
      confidence = StrictMath.min(confidence, velocity.get().estimate().confidence().value());
    }
    if (model == Model.CONSTANT_ACCELERATION) {
      if (!acceleration.isPresent()) return Optional.empty();
      requireCompatible(position, acceleration.get(), VectorEstimate.Quantity.ACCELERATION_MPS2);
      if (!acceleration.get().estimate().value().isPresent()) return Optional.empty();
      p = p.add(acceleration.get().estimate().value().get().multiply(.5 * dt * dt));
      confidence = StrictMath.min(confidence, acceleration.get().estimate().confidence().value());
    }
    return Optional.of(
        new TimedVectorEstimate(
            target,
            new VectorEstimate(
                p.frame(),
                VectorEstimate.Quantity.POSITION_METERS,
                Optional.of(p),
                Optional.empty(),
                new Confidence(confidence))));
  }

  public static Vector3 velocity(Vector3 velocity, Vector3 acceleration, double seconds) {
    NumericPolicy.nonNegative(seconds);
    return velocity.add(acceleration.multiply(seconds));
  }

  private static void requireCompatible(
      TimedVectorEstimate reference, TimedVectorEstimate sample, VectorEstimate.Quantity quantity) {
    reference.estimate().frame().requireSame(sample.estimate().frame());
    reference.time().requireSameClock(sample.time());
    if (!reference.time().equals(sample.time()) || sample.estimate().quantity() != quantity)
      throw new IllegalArgumentException("Align prediction inputs and units");
  }
}
