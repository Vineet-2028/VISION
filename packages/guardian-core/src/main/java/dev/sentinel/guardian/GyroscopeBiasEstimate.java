package dev.sentinel.guardian;

import java.util.Objects;

/** Supplied bias only; no learning. Estimate units must be radians/second in DEVICE. */
public final class GyroscopeBiasEstimate implements TimedObservation {
  private final TimedVectorEstimate bias;

  public GyroscopeBiasEstimate(TimedVectorEstimate bias) {
    this.bias = Objects.requireNonNull(bias, "bias");
    if (bias.estimate().frame().kind() != FrameKind.DEVICE
        || bias.estimate().quantity() != VectorEstimate.Quantity.ANGULAR_VELOCITY_RADPS)
      throw new IllegalArgumentException("Gyro bias units/frame");
  }

  public MonotonicTime time() {
    return bias.time();
  }

  public VectorEstimate estimate() {
    return bias.estimate();
  }
}
