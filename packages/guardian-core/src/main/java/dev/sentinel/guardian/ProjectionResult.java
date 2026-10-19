package dev.sentinel.guardian;

import java.util.Optional;

/** Mathematical validity and sensor membership are separate. */
public final class ProjectionResult {
  private final Optional<PixelPoint> pixel;
  private final boolean insideImage;

  private ProjectionResult(Optional<PixelPoint> pixel, boolean insideImage) {
    this.pixel = pixel;
    this.insideImage = insideImage;
  }

  static ProjectionResult available(PixelPoint pixel, boolean inside) {
    return new ProjectionResult(Optional.of(pixel), inside);
  }

  public static ProjectionResult unavailable() {
    return new ProjectionResult(Optional.empty(), false);
  }

  public Optional<PixelPoint> pixel() {
    return pixel;
  }

  public boolean insideImage() {
    return insideImage;
  }

  public boolean isValid() {
    return pixel.isPresent();
  }
}
