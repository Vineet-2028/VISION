package dev.sentinel.guardian;

import java.util.Objects;

/** Identifies one calibrated frame instance, not just an axis convention. */
public final class FrameId {
  private final FrameKind kind;
  private final String id;

  public FrameId(FrameKind kind, String id) {
    this.kind = Objects.requireNonNull(kind, "kind");
    this.id = NumericPolicy.identity(id);
  }

  public void requireSame(FrameId other) {
    if (!equals(other)) throw new IllegalArgumentException("Incompatible coordinate frames");
  }

  public void requireSpatial() {
    if (kind == FrameKind.IMAGE)
      throw new IllegalArgumentException("Image coordinates are not metric 3D coordinates");
  }

  @Override
  public boolean equals(Object other) {
    if (!(other instanceof FrameId)) return false;
    FrameId frame = (FrameId) other;
    return kind == frame.kind() && id.equals(frame.id());
  }

  @Override
  public int hashCode() {
    return 31 * kind.hashCode() + id.hashCode();
  }

  public FrameKind kind() {
    return kind;
  }

  public String id() {
    return id;
  }
}
