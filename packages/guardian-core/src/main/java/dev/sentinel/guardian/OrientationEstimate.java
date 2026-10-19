package dev.sentinel.guardian;

import java.util.Objects;
import java.util.Optional;
import java.util.OptionalDouble;

/**
 * Rotation mapping from->to at time; optional angular standard deviation in radians (not
 * covariance).
 */
public final class OrientationEstimate implements TimedObservation {
  private final FrameId from;
  private final FrameId to;
  private final MonotonicTime time;
  private final Optional<Quaternion> rotation;
  private final OptionalDouble standardDeviationRadians;
  private final Confidence confidence;

  public OrientationEstimate(
      FrameId from,
      FrameId to,
      MonotonicTime time,
      Optional<Quaternion> rotation,
      OptionalDouble standardDeviationRadians,
      Confidence confidence) {
    from.requireSpatial();
    to.requireSpatial();
    this.from = from;
    this.to = to;
    this.time = Objects.requireNonNull(time, "time");
    this.rotation = Objects.requireNonNull(rotation, "rotation");
    this.standardDeviationRadians =
        Objects.requireNonNull(standardDeviationRadians, "standardDeviationRadians");
    if (standardDeviationRadians.isPresent()) {
      NumericPolicy.nonNegative(standardDeviationRadians.getAsDouble());
      if (!rotation.isPresent())
        throw new IllegalArgumentException("Unknown rotation cannot carry uncertainty");
    }
    this.confidence = Objects.requireNonNull(confidence, "confidence");
    if (!rotation.isPresent() && confidence.value() != 0)
      throw new IllegalArgumentException("Unknown rotation requires zero confidence");
  }

  public FrameId from() {
    return from;
  }

  public FrameId to() {
    return to;
  }

  public MonotonicTime time() {
    return time;
  }

  public Optional<Quaternion> rotation() {
    return rotation;
  }

  public OptionalDouble standardDeviationRadians() {
    return standardDeviationRadians;
  }

  public Confidence confidence() {
    return confidence;
  }
}
