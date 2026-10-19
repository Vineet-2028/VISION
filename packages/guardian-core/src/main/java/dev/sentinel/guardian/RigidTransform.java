package dev.sentinel.guardian;

import java.util.Objects;

/** p_to = R * p_from + translationInToMeters. No calibration is inferred. */
public final class RigidTransform {
  private final FrameId from;
  private final FrameId to;
  private final Quaternion rotation;
  private final Vector3 translationInToMeters;

  public RigidTransform(
      FrameId from, FrameId to, Quaternion rotation, Vector3 translationInToMeters) {
    this.from = Objects.requireNonNull(from, "from");
    this.to = Objects.requireNonNull(to, "to");
    from.requireSpatial();
    to.requireSpatial();
    this.rotation = Objects.requireNonNull(rotation, "rotation");
    to.requireSame(translationInToMeters.frame());
    this.translationInToMeters = translationInToMeters;
  }

  public Vector3 transformPoint(Vector3 point) {
    return transformDirection(point).add(translationInToMeters);
  }

  public Vector3 transformDirection(Vector3 direction) {
    from.requireSame(direction.frame());
    return rotation.rotateInto(direction, to);
  }

  public RigidTransform inverse() {
    Quaternion inverse = rotation.conjugate();
    return new RigidTransform(
        to, from, inverse, inverse.rotateInto(translationInToMeters.multiply(-1), from));
  }

  /** Apply this transform first, then next. */
  public RigidTransform then(RigidTransform next) {
    to.requireSame(next.from());
    return new RigidTransform(
        from,
        next.to(),
        next.rotation().multiply(rotation),
        next.transformPoint(translationInToMeters));
  }

  public FrameId from() {
    return from;
  }

  public FrameId to() {
    return to;
  }

  public Quaternion rotation() {
    return rotation;
  }

  public Vector3 translationInToMeters() {
    return translationInToMeters;
  }
}
