package dev.sentinel.guardian;

import java.util.Objects;

/** Observation contract only; never produces a detection. Category is producer-namespaced. */
public final class Detection2D {
  private final String category;
  private final Confidence confidence;
  private final BoundingBox2D box;
  private final FrameMetadata frame;

  public Detection2D(
      String category, Confidence confidence, BoundingBox2D box, FrameMetadata frame) {
    this.category = NumericPolicy.identity(category);
    this.confidence = Objects.requireNonNull(confidence, "confidence");
    this.box = Objects.requireNonNull(box, "box");
    this.frame = Objects.requireNonNull(frame, "frame");
  }

  public String category() {
    return category;
  }

  public Confidence confidence() {
    return confidence;
  }

  public BoundingBox2D box() {
    return box;
  }

  public FrameMetadata frame() {
    return frame;
  }
}
