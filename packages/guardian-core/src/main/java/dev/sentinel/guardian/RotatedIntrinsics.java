package dev.sentinel.guardian;

/**
 * Ideal intrinsics after buffer rotation, with the REQUIRED optical-axis basis change. Distortion
 * calibration is not implicitly reused. Prefer inverse image mapping to original calibration.
 */
public final class RotatedIntrinsics {
  private final CameraIntrinsics intrinsics;
  private final RigidTransform originalCameraToRotatedCamera;
  private final ImageTransform imageTransform;

  public RotatedIntrinsics(
      CameraIntrinsics original, FrameId newImage, FrameId newCamera, int quarterTurns) {
    if (newCamera.kind() != FrameKind.CAMERA || newCamera.equals(original.cameraFrame()))
      throw new IllegalArgumentException("A distinct rotated CAMERA identity is required");
    imageTransform = ImageTransform.rotateClockwise(original.imageSize(), newImage, quarterTurns);
    PixelPoint principal =
        imageTransform.forward(
            new PixelPoint(original.imageFrame(), original.cxPixels(), original.cyPixels()));
    boolean swap = quarterTurns % 2 != 0;
    intrinsics =
        new CameraIntrinsics(
            newCamera,
            newImage,
            imageTransform.to().width(),
            imageTransform.to().height(),
            swap ? original.fyPixels() : original.fxPixels(),
            swap ? original.fxPixels() : original.fyPixels(),
            principal.u(),
            principal.v());
    double half = quarterTurns * StrictMath.PI / 4;
    originalCameraToRotatedCamera =
        new RigidTransform(
            original.cameraFrame(),
            newCamera,
            new Quaternion(StrictMath.cos(half), 0, 0, StrictMath.sin(half)),
            new Vector3(newCamera, 0, 0, 0));
  }

  public CameraIntrinsics intrinsics() {
    return intrinsics;
  }

  public RigidTransform originalCameraToRotatedCamera() {
    return originalCameraToRotatedCamera;
  }

  public ImageTransform imageTransform() {
    return imageTransform;
  }
}
