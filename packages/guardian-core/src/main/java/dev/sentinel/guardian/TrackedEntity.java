package dev.sentinel.guardian;

import java.util.Objects;

/** Immutable snapshot, not a tracker. All estimates refer to latestObservationTime. */
public final class TrackedEntity {
  public enum Lifecycle {
    TENTATIVE,
    CONFIRMED,
    LOST
  }

  private final String trackId;
  private final String category;
  private final MonotonicTime latestObservationTime;
  private final VectorEstimate position;
  private final VectorEstimate velocity;
  private final VectorEstimate acceleration;
  private final Confidence confidence;
  private final Lifecycle lifecycle;
  private final long observationCount;

  public TrackedEntity(
      String trackId,
      String category,
      MonotonicTime latestObservationTime,
      VectorEstimate position,
      VectorEstimate velocity,
      VectorEstimate acceleration,
      Confidence confidence,
      Lifecycle lifecycle,
      long observationCount) {
    this.trackId = NumericPolicy.identity(trackId);
    this.category = NumericPolicy.identity(category);
    this.latestObservationTime =
        Objects.requireNonNull(latestObservationTime, "latestObservationTime");
    if (position.quantity() != VectorEstimate.Quantity.POSITION_METERS
        || velocity.quantity() != VectorEstimate.Quantity.VELOCITY_MPS
        || acceleration.quantity() != VectorEstimate.Quantity.ACCELERATION_MPS2)
      throw new IllegalArgumentException("Incorrect kinematic quantity");
    position.frame().requireSame(velocity.frame());
    position.frame().requireSame(acceleration.frame());
    this.position = position;
    this.velocity = velocity;
    this.acceleration = acceleration;
    this.confidence = Objects.requireNonNull(confidence, "confidence");
    this.lifecycle = Objects.requireNonNull(lifecycle, "lifecycle");
    if (observationCount < 1) throw new IllegalArgumentException("A track needs an observation");
    this.observationCount = observationCount;
  }

  public String trackId() {
    return trackId;
  }

  public String category() {
    return category;
  }

  public MonotonicTime latestObservationTime() {
    return latestObservationTime;
  }

  public VectorEstimate position() {
    return position;
  }

  public VectorEstimate velocity() {
    return velocity;
  }

  public VectorEstimate acceleration() {
    return acceleration;
  }

  public Confidence confidence() {
    return confidence;
  }

  public Lifecycle lifecycle() {
    return lifecycle;
  }

  public long observationCount() {
    return observationCount;
  }
}
