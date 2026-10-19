package dev.sentinel.guardian;

import java.util.Objects;
import java.util.Optional;
import java.util.OptionalDouble;

/**
 * Supplied DEVICE -> LOCAL_WORLD pose at a capture time; no sensor integration or interpolation.
 */
public final class DevicePoseEstimate implements TimedObservation {
  private final MonotonicTime time;
  private final Optional<RigidTransform> transform;
  private final Confidence confidence;
  private final OptionalDouble positionStdMeters, orientationStdRadians;

  public DevicePoseEstimate(
      MonotonicTime time,
      Optional<RigidTransform> transform,
      Confidence confidence,
      OptionalDouble positionStdMeters,
      OptionalDouble orientationStdRadians) {
    this.time = Objects.requireNonNull(time, "time");
    this.transform = Objects.requireNonNull(transform, "transform");
    this.confidence = Objects.requireNonNull(confidence, "confidence");
    this.positionStdMeters = Objects.requireNonNull(positionStdMeters, "positionStdMeters");
    this.orientationStdRadians =
        Objects.requireNonNull(orientationStdRadians, "orientationStdRadians");
    if (positionStdMeters.isPresent()) NumericPolicy.nonNegative(positionStdMeters.getAsDouble());
    if (orientationStdRadians.isPresent())
      NumericPolicy.nonNegative(orientationStdRadians.getAsDouble());
    if (!transform.isPresent()
        && (confidence.value() != 0
            || positionStdMeters.isPresent()
            || orientationStdRadians.isPresent()))
      throw new IllegalArgumentException("Unknown pose cannot carry certainty");
    if (transform.isPresent()
        && (transform.get().from().kind() != FrameKind.DEVICE
            || transform.get().to().kind() != FrameKind.LOCAL_WORLD))
      throw new IllegalArgumentException("Expected DEVICE -> LOCAL_WORLD");
  }

  public MonotonicTime time() {
    return time;
  }

  public Optional<RigidTransform> transform() {
    return transform;
  }

  public Confidence confidence() {
    return confidence;
  }

  public OptionalDouble positionStdMeters() {
    return positionStdMeters;
  }

  public OptionalDouble orientationStdRadians() {
    return orientationStdRadians;
  }
}
