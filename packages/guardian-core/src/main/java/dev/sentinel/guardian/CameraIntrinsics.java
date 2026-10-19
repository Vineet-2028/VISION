package dev.sentinel.guardian;

import java.util.Objects;

/** Zero-skew ideal pinhole intrinsics in continuous pixel-edge coordinates. */
public final class CameraIntrinsics {
  private final FrameId cameraFrame;
  private final FrameId imageFrame;
  private final int widthPixels;
  private final int heightPixels;
  private final double fxPixels;
  private final double fyPixels;
  private final double cxPixels;
  private final double cyPixels;

  public CameraIntrinsics(
      FrameId cameraFrame,
      FrameId imageFrame,
      int widthPixels,
      int heightPixels,
      double fxPixels,
      double fyPixels,
      double cxPixels,
      double cyPixels) {
    this.cameraFrame = Objects.requireNonNull(cameraFrame, "cameraFrame");
    this.imageFrame = Objects.requireNonNull(imageFrame, "imageFrame");
    if (cameraFrame.kind() != FrameKind.CAMERA
        || imageFrame.kind() != FrameKind.IMAGE
        || widthPixels <= 0
        || heightPixels <= 0)
      throw new IllegalArgumentException("Invalid camera/image frame or dimensions");
    if (NumericPolicy.finite(fxPixels) <= 0 || NumericPolicy.finite(fyPixels) <= 0)
      throw new IllegalArgumentException("Focal lengths must be positive");
    this.widthPixels = widthPixels;
    this.heightPixels = heightPixels;
    this.fxPixels = fxPixels;
    this.fyPixels = fyPixels;
    // Crops can legitimately place the principal point outside the image.
    this.cxPixels = NumericPolicy.finite(cxPixels);
    this.cyPixels = NumericPolicy.finite(cyPixels);
  }

  public FrameId cameraFrame() {
    return cameraFrame;
  }

  public FrameId imageFrame() {
    return imageFrame;
  }

  public int widthPixels() {
    return widthPixels;
  }

  public int heightPixels() {
    return heightPixels;
  }

  public double fxPixels() {
    return fxPixels;
  }

  public double fyPixels() {
    return fyPixels;
  }

  public double cxPixels() {
    return cxPixels;
  }

  public double cyPixels() {
    return cyPixels;
  }

  public ImageSize imageSize() {
    return new ImageSize(imageFrame, widthPixels, heightPixels);
  }

  public double leftAngleRadians() {
    return StrictMath.atan2(-cxPixels, fxPixels);
  }

  public double rightAngleRadians() {
    return StrictMath.atan2(widthPixels - cxPixels, fxPixels);
  }

  public double topAngleRadians() {
    return StrictMath.atan2(cyPixels, fyPixels);
  }

  public double bottomAngleRadians() {
    return StrictMath.atan2(cyPixels - heightPixels, fyPixels);
  }

  public double horizontalFovRadians() {
    return rightAngleRadians() - leftAngleRadians();
  }

  public double verticalFovRadians() {
    return topAngleRadians() - bottomAngleRadians();
  }

  /** Explicit importer entry point: skew is not silently ignored. */
  public static CameraIntrinsics withSkew(
      FrameId camera,
      FrameId image,
      int width,
      int height,
      double fx,
      double fy,
      double cx,
      double cy,
      double skewPixels) {
    if (NumericPolicy.finite(skewPixels) != 0)
      throw new IllegalArgumentException("Nonzero skew is unsupported");
    return new CameraIntrinsics(camera, image, width, height, fx, fy, cx, cy);
  }

  public CameraIntrinsics scaledTo(ImageSize target) {
    ImageTransform.requireDistinctFrames(imageFrame, target.frame());
    double sx = (double) target.width() / widthPixels, sy = (double) target.height() / heightPixels;
    return new CameraIntrinsics(
        cameraFrame,
        target.frame(),
        target.width(),
        target.height(),
        sx * fxPixels,
        sy * fyPixels,
        sx * cxPixels,
        sy * cyPixels);
  }

  public CameraIntrinsics croppedTo(ImageSize target, int left, int top) {
    ImageTransform.requireDistinctFrames(imageFrame, target.frame());
    if (left < 0
        || top < 0
        || (long) left + target.width() > widthPixels
        || (long) top + target.height() > heightPixels)
      throw new IllegalArgumentException("Crop outside source");
    return new CameraIntrinsics(
        cameraFrame,
        target.frame(),
        target.width(),
        target.height(),
        fxPixels,
        fyPixels,
        cxPixels - left,
        cyPixels - top);
  }
}
