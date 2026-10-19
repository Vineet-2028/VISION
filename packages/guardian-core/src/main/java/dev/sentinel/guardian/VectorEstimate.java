package dev.sentinel.guardian;

import java.util.Objects;
import java.util.Optional;

/**
 * SI vector with optional per-axis standard deviations; cross-axis covariance is not represented.
 */
public final class VectorEstimate {
  public enum Quantity {
    POSITION_METERS,
    VELOCITY_MPS,
    ACCELERATION_MPS2,
    SPECIFIC_FORCE_MPS2,
    ANGULAR_VELOCITY_RADPS
  }

  private final FrameId frame;
  private final Quantity quantity;
  private final Optional<Vector3> value;
  private final Optional<Vector3> standardDeviation;
  private final Confidence confidence;

  public VectorEstimate(
      FrameId frame,
      Quantity quantity,
      Optional<Vector3> value,
      Optional<Vector3> standardDeviation,
      Confidence confidence) {
    frame.requireSpatial();
    this.frame = frame;
    this.quantity = Objects.requireNonNull(quantity, "quantity");
    this.value = Objects.requireNonNull(value, "value");
    this.standardDeviation = Objects.requireNonNull(standardDeviation, "standardDeviation");
    this.confidence = Objects.requireNonNull(confidence, "confidence");
    if (value.isPresent()) frame.requireSame(value.get().frame());
    if (!value.isPresent() && (standardDeviation.isPresent() || confidence.value() != 0))
      throw new IllegalArgumentException(
          "Unknown vector requires no uncertainty and zero confidence");
    if (standardDeviation.isPresent()) {
      Vector3 std = standardDeviation.get();
      frame.requireSame(std.frame());
      NumericPolicy.nonNegative(std.x());
      NumericPolicy.nonNegative(std.y());
      NumericPolicy.nonNegative(std.z());
    }
  }

  public FrameId frame() {
    return frame;
  }

  public Quantity quantity() {
    return quantity;
  }

  public Optional<Vector3> value() {
    return value;
  }

  public Optional<Vector3> standardDeviation() {
    return standardDeviation;
  }

  public Confidence confidence() {
    return confidence;
  }
}
