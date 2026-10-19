package dev.sentinel.guardian;

import java.util.Objects;
import java.util.Optional;

/**
 * Calibrated central camera geometry. No inference, visibility occlusion, or distance estimation.
 */
public final class CameraModel {
  private final CameraCalibration calibration;
  private final GeometryPolicy policy;

  public CameraModel(CameraCalibration calibration, GeometryPolicy policy) {
    this.calibration = Objects.requireNonNull(calibration, "calibration");
    this.policy = Objects.requireNonNull(policy, "policy");
  }

  public CameraCalibration calibration() {
    return calibration;
  }

  public Optional<Vector3> pixelToCameraRay(PixelPoint pixel, FrameMetadata frame) {
    calibration.requireFrame(frame);
    calibration.intrinsics().imageFrame().requireSame(pixel.frame());
    if (calibration.quality().state() == CalibrationQuality.State.INVALID) return Optional.empty();
    CameraIntrinsics k = calibration.intrinsics();
    try {
      CameraPlanePoint distorted =
          new CameraPlanePoint(
              k.cameraFrame(),
              (pixel.u() - k.cxPixels()) / k.fxPixels(),
              (pixel.v() - k.cyPixels()) / k.fyPixels());
      Optional<CameraPlanePoint> ideal = calibration.distortion().undistort(distorted, policy);
      if (!ideal.isPresent()) return Optional.empty();
      k.cameraFrame().requireSame(ideal.get().frame());
      return Optional.of(
          new Vector3(k.cameraFrame(), ideal.get().x(), ideal.get().y(), 1).normalized());
    } catch (IllegalArgumentException numericFailure) {
      return Optional.empty();
    }
  }

  public ProjectionResult cameraPointToPixel(Vector3 point) {
    CameraIntrinsics k = calibration.intrinsics();
    k.cameraFrame().requireSame(point.frame());
    if (point.z() <= policy.nearPlaneMeters()
        || calibration.quality().state() == CalibrationQuality.State.INVALID)
      return ProjectionResult.unavailable();
    try {
      Optional<CameraPlanePoint> distorted =
          calibration
              .distortion()
              .distort(
                  new CameraPlanePoint(
                      k.cameraFrame(), point.x() / point.z(), point.y() / point.z()));
      if (!distorted.isPresent()) return ProjectionResult.unavailable();
      k.cameraFrame().requireSame(distorted.get().frame());
      PixelPoint pixel =
          new PixelPoint(
              k.imageFrame(),
              k.fxPixels() * distorted.get().x() + k.cxPixels(),
              k.fyPixels() * distorted.get().y() + k.cyPixels());
      return ProjectionResult.available(pixel, k.imageSize().contains(pixel));
    } catch (IllegalArgumentException numericFailure) {
      return ProjectionResult.unavailable();
    }
  }

  public Optional<DirectionAngles> bearing(PixelPoint pixel, FrameMetadata frame) {
    Optional<Vector3> ray = pixelToCameraRay(pixel, frame);
    if (!ray.isPresent()) return Optional.empty();
    try {
      return Optional.of(DirectionAngles.fromCameraDirection(ray.get()));
    } catch (IllegalArgumentException numericFailure) {
      return Optional.empty();
    }
  }

  public Optional<Vector3> groundContactRayCandidate(Detection2D detection) {
    calibration.requireFrame(detection.frame());
    PixelBox box = PixelBox.fromNormalized(detection.box(), calibration.intrinsics().imageSize());
    return pixelToCameraRay(box.bottomCenter(), detection.frame());
  }

  public Optional<DirectionAngles> detectionBearing(Detection2D detection) {
    calibration.requireFrame(detection.frame());
    return bearing(
        PixelBox.fromNormalized(detection.box(), calibration.intrinsics().imageSize()).center(),
        detection.frame());
  }

  public Optional<AngularExtent> angularExtent(PixelBox box, FrameMetadata frame) {
    calibration.intrinsics().imageFrame().requireSame(box.frame());
    Optional<DirectionAngles> a = bearing(box.topLeft(), frame),
        b = bearing(box.topRight(), frame),
        c = bearing(box.bottomLeft(), frame),
        d = bearing(box.bottomRight(), frame);
    if (!a.isPresent() || !b.isPresent() || !c.isPresent() || !d.isPresent())
      return Optional.empty();
    return Optional.of(
        new AngularExtent(
            StrictMath.min(
                StrictMath.min(a.get().azimuthRadians(), b.get().azimuthRadians()),
                StrictMath.min(c.get().azimuthRadians(), d.get().azimuthRadians())),
            StrictMath.max(
                StrictMath.max(a.get().azimuthRadians(), b.get().azimuthRadians()),
                StrictMath.max(c.get().azimuthRadians(), d.get().azimuthRadians())),
            StrictMath.max(
                StrictMath.max(a.get().elevationRadians(), b.get().elevationRadians()),
                StrictMath.max(c.get().elevationRadians(), d.get().elevationRadians())),
            StrictMath.min(
                StrictMath.min(a.get().elevationRadians(), b.get().elevationRadians()),
                StrictMath.min(c.get().elevationRadians(), d.get().elevationRadians()))));
  }
}
