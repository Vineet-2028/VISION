package dev.sentinel.guardian;

import java.util.Objects;
import java.util.Optional;

/** Immutable effective camera calibration. Identity must change when geometry changes. */
public final class CameraCalibration {
  private final CalibrationId id;
  private final CameraIntrinsics intrinsics;
  private final LensDistortionModel distortion;
  private final CalibrationQuality quality;
  private final Optional<String> metadata;

  public CameraCalibration(
      CalibrationId id,
      CameraIntrinsics intrinsics,
      LensDistortionModel distortion,
      CalibrationQuality quality,
      Optional<String> metadata) {
    this.id = Objects.requireNonNull(id, "id");
    this.intrinsics = Objects.requireNonNull(intrinsics, "intrinsics");
    this.distortion = Objects.requireNonNull(distortion, "distortion");
    this.quality = Objects.requireNonNull(quality, "quality");
    this.metadata = Objects.requireNonNull(metadata, "metadata");
  }

  public void requireFrame(FrameMetadata frame) {
    if (!frame.calibrationId().isPresent())
      throw new IllegalArgumentException("Frame has no calibration identity");
    id.requireSame(frame.calibrationId().get());
    intrinsics.imageFrame().requireSame(frame.imageFrame());
    if (intrinsics.widthPixels() != frame.widthPixels()
        || intrinsics.heightPixels() != frame.heightPixels())
      throw new IllegalArgumentException("Calibration resolution mismatch");
  }

  public CalibrationId id() {
    return id;
  }

  public CameraIntrinsics intrinsics() {
    return intrinsics;
  }

  public LensDistortionModel distortion() {
    return distortion;
  }

  public CalibrationQuality quality() {
    return quality;
  }

  public Optional<String> metadata() {
    return metadata;
  }
}
