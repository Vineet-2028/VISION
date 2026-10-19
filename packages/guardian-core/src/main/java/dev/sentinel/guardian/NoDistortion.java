package dev.sentinel.guardian;

import java.util.Objects;
import java.util.Optional;

public final class NoDistortion implements LensDistortionModel {
  @Override
  public Optional<CameraPlanePoint> distort(CameraPlanePoint point) {
    return Optional.of(Objects.requireNonNull(point, "point"));
  }

  @Override
  public Optional<CameraPlanePoint> undistort(CameraPlanePoint point, GeometryPolicy policy) {
    Objects.requireNonNull(policy, "policy");
    return distort(point);
  }

  @Override
  public String modelName() {
    return "none";
  }
}
