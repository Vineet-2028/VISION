package dev.sentinel.guardian;

import java.util.List;

/** Pure window classifier. Constant translational velocity is indistinguishable from rest. */
public final class StationaryDetector {
  public enum Result {
    STATIONARY_CANDIDATE,
    MOVING,
    INSUFFICIENT_DATA
  }

  private StationaryDetector() {}

  public static Result evaluate(List<ImuSample> samples, StationaryDetectionPolicy policy) {
    if (samples.size() < policy.minimumSamples) return Result.INSUFFICIENT_DATA;
    Statistics force = new Statistics();
    boolean moving = false;
    ImuSample previous = null;
    FrameId frame = samples.get(0).rawSpecificForceMps2().frame();
    if (frame.kind() != FrameKind.DEVICE) throw new IllegalArgumentException("DEVICE IMU required");
    for (ImuSample sample : samples) {
      frame.requireSame(sample.rawSpecificForceMps2().frame());
      if (previous != null) {
        long gap = sample.time().elapsedNanosSince(previous.time());
        if (gap == 0) throw new IllegalArgumentException("Duplicate sample");
        if (gap > policy.maximumGapNanos) return Result.INSUFFICIENT_DATA;
      }
      double magnitude = NumericPolicy.finite(sample.rawSpecificForceMps2().magnitude());
      force.add(magnitude);
      moving |=
          sample.angularVelocityRadiansPerSecond().magnitude() > policy.maxGyro
              || StrictMath.abs(magnitude - policy.gravityMagnitude) > policy.maxGravityDeviation;
      previous = sample;
    }
    if (samples.get(samples.size() - 1).time().elapsedNanosSince(samples.get(0).time())
        < policy.minimumSpanNanos) return Result.INSUFFICIENT_DATA;
    return moving || force.populationVariance() > policy.maxForceVariance
        ? Result.MOVING
        : Result.STATIONARY_CANDIDATE;
  }
}
