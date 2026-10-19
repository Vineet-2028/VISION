package dev.sentinel.guardian;

import java.util.Objects;

/** Supplied specific-force bias in DEVICE m/s^2; no stationary calibration is inferred. */
public final class AccelerometerBiasEstimate implements TimedObservation {
  private final TimedVectorEstimate bias;

  public AccelerometerBiasEstimate(TimedVectorEstimate bias) {
    this.bias = Objects.requireNonNull(bias, "bias");
    if (bias.estimate().frame().kind() != FrameKind.DEVICE
        || bias.estimate().quantity() != VectorEstimate.Quantity.SPECIFIC_FORCE_MPS2)
      throw new IllegalArgumentException("Accelerometer bias units/frame");
  }

  public MonotonicTime time() {
    return bias.time();
  }

  public VectorEstimate estimate() {
    return bias.estimate();
  }
}
