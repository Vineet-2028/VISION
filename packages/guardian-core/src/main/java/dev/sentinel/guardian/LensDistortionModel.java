package dev.sentinel.guardian;

import java.util.Optional;

/**
 * Implementations must be immutable, deterministic, bounded and preserve CAMERA identity. Empty
 * means outside the calibrated domain, numeric failure, or no converged inverse.
 */
public interface LensDistortionModel {
  Optional<CameraPlanePoint> distort(CameraPlanePoint ideal);

  Optional<CameraPlanePoint> undistort(CameraPlanePoint distorted, GeometryPolicy policy);

  String modelName();
}
