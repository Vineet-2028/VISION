package dev.sentinel.guardian;

import java.util.Objects;
import java.util.Optional;
import java.util.OptionalDouble;

/** Supplied local planar approximation at time; not an assertion that the world is flat. */
public final class GroundPlaneEstimate {
  private final Optional<Plane3D> plane;
  private final MonotonicTime time;
  private final Confidence confidence;
  private final OptionalDouble offsetStdMeters, normalStdRadians;
  private final String source;

  public GroundPlaneEstimate(
      Optional<Plane3D> plane,
      MonotonicTime time,
      Confidence confidence,
      OptionalDouble offsetStdMeters,
      OptionalDouble normalStdRadians,
      String source) {
    this.plane = Objects.requireNonNull(plane, "plane");
    this.time = Objects.requireNonNull(time, "time");
    this.confidence = Objects.requireNonNull(confidence, "confidence");
    this.offsetStdMeters = Objects.requireNonNull(offsetStdMeters, "offsetStdMeters");
    this.normalStdRadians = Objects.requireNonNull(normalStdRadians, "normalStdRadians");
    this.source = NumericPolicy.identity(source);
    if (plane.isPresent() && plane.get().frame().kind() != FrameKind.LOCAL_WORLD)
      throw new IllegalArgumentException("Ground requires LOCAL_WORLD");
    if (offsetStdMeters.isPresent()) NumericPolicy.nonNegative(offsetStdMeters.getAsDouble());
    if (normalStdRadians.isPresent()) NumericPolicy.nonNegative(normalStdRadians.getAsDouble());
    if (!plane.isPresent()
        && (confidence.value() != 0 || offsetStdMeters.isPresent() || normalStdRadians.isPresent()))
      throw new IllegalArgumentException("Unknown plane cannot carry certainty");
  }

  public Optional<Plane3D> plane() {
    return plane;
  }

  public MonotonicTime time() {
    return time;
  }

  public Confidence confidence() {
    return confidence;
  }

  public OptionalDouble offsetStdMeters() {
    return offsetStdMeters;
  }

  public OptionalDouble normalStdRadians() {
    return normalStdRadians;
  }

  public String source() {
    return source;
  }
}
