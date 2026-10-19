package dev.sentinel.guardian;

import java.util.Objects;

/** Sensor membership via calibrated projection. Does not determine occlusion. */
public final class CameraFrustum {
  private final CameraModel model;

  public CameraFrustum(CameraModel model) {
    this.model = Objects.requireNonNull(model, "model");
  }

  public boolean containsCameraPoint(Vector3 point) {
    return model.cameraPointToPixel(point).insideImage();
  }
}
