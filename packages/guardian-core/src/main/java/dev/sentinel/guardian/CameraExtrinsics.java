package dev.sentinel.guardian;

import java.util.Objects;

/** Camera optical center to body reference; translation in meters, rotation Hamilton quaternion. */
public final class CameraExtrinsics {
  private final CalibrationId cameraCalibration;
  private final String version;
  private final RigidTransform cameraToDevice;

  public CameraExtrinsics(
      CalibrationId cameraCalibration, String version, RigidTransform cameraToDevice) {
    this.cameraCalibration = Objects.requireNonNull(cameraCalibration, "cameraCalibration");
    this.version = NumericPolicy.identity(version);
    if (cameraToDevice.from().kind() != FrameKind.CAMERA
        || cameraToDevice.to().kind() != FrameKind.DEVICE)
      throw new IllegalArgumentException("Expected CAMERA -> DEVICE");
    this.cameraToDevice = cameraToDevice;
  }

  public CalibrationId cameraCalibration() {
    return cameraCalibration;
  }

  public String version() {
    return version;
  }

  public RigidTransform cameraToDevice() {
    return cameraToDevice;
  }
}
