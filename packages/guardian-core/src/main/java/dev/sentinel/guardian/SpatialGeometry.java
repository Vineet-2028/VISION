package dev.sentinel.guardian;

import java.util.Optional;

/** Deterministic transform chains; pose and ground must be supplied at the ray capture time. */
public final class SpatialGeometry {
  private SpatialGeometry() {}

  public static Optional<Ray3D> pixelToWorldRay(
      PixelPoint pixel,
      FrameMetadata frame,
      CameraModel model,
      CameraExtrinsics extrinsics,
      DevicePoseEstimate pose) {
    model.calibration().requireFrame(frame);
    model.calibration().id().requireSame(extrinsics.cameraCalibration());
    model.calibration().intrinsics().cameraFrame().requireSame(extrinsics.cameraToDevice().from());
    frame.captureTime().requireSameClock(pose.time());
    if (!frame.captureTime().equals(pose.time()))
      throw new IllegalArgumentException("Pose must be evaluated at capture time");
    if (!pose.transform().isPresent()) return Optional.empty();
    RigidTransform transform = extrinsics.cameraToDevice().then(pose.transform().get());
    Optional<Vector3> direction = model.pixelToCameraRay(pixel, frame);
    if (!direction.isPresent()) return Optional.empty();
    try {
      return Optional.of(
          new Ray3D(
              transform.transformPoint(new Vector3(transform.from(), 0, 0, 0)),
              transform.transformDirection(direction.get()),
              Optional.of(frame.captureTime())));
    } catch (IllegalArgumentException numericFailure) {
      return Optional.empty();
    }
  }

  public static Optional<Ray3D> groundContactRayCandidate(
      Detection2D detection,
      CameraModel model,
      CameraExtrinsics extrinsics,
      DevicePoseEstimate pose) {
    PixelPoint bottom =
        PixelBox.fromNormalized(detection.box(), model.calibration().intrinsics().imageSize())
            .bottomCenter();
    return pixelToWorldRay(bottom, detection.frame(), model, extrinsics, pose);
  }

  public static Optional<GroundIntersectionCandidate> groundIntersection(
      Ray3D ray, GroundPlaneEstimate ground, GeometryPolicy policy) {
    if (ray.frame().kind() != FrameKind.LOCAL_WORLD)
      throw new IllegalArgumentException("World ray required");
    if (!ground.plane().isPresent()) return Optional.empty();
    ray.frame().requireSame(ground.plane().get().frame());
    if (!ray.time().isPresent())
      throw new IllegalArgumentException("Ground intersection requires capture time");
    ray.time().get().requireSameClock(ground.time());
    if (!ray.time().get().equals(ground.time()))
      throw new IllegalArgumentException("Ground must be evaluated at capture time");
    Optional<Vector3> point = ground.plane().get().rayIntersection(ray, policy);
    return point.isPresent()
        ? Optional.of(new GroundIntersectionCandidate(point.get(), ground, ray))
        : Optional.empty();
  }
}
