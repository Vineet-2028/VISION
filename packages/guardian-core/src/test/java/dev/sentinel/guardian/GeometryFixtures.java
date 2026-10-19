package dev.sentinel.guardian;

import java.util.Optional;
import java.util.OptionalDouble;
import java.util.OptionalLong;

final class GeometryFixtures {
  static final FrameId C = new FrameId(FrameKind.CAMERA, "rear");
  static final FrameId I = new FrameId(FrameKind.IMAGE, "rear:cal1");
  static final FrameId D = new FrameId(FrameKind.DEVICE, "body");
  static final FrameId W = new FrameId(FrameKind.LOCAL_WORLD, "session");
  static final CalibrationId ID = new CalibrationId("rear", "cal1");
  static final MonotonicTime TIME = new MonotonicTime("sensor", 1000);
  static final GeometryPolicy POLICY = GeometryPolicy.defaults();

  private GeometryFixtures() {}

  static CameraIntrinsics intrinsics() {
    return new CameraIntrinsics(C, I, 1000, 1000, 1000, 1000, 500, 500);
  }

  static CameraModel model(CameraIntrinsics k, LensDistortionModel distortion) {
    return new CameraModel(
        new CameraCalibration(
            ID,
            k,
            distortion,
            new CalibrationQuality(
                CalibrationQuality.State.VALID,
                OptionalDouble.of(.2),
                OptionalLong.of(20),
                Optional.empty()),
            Optional.empty()),
        POLICY);
  }

  static CameraModel model() {
    return model(intrinsics(), new NoDistortion());
  }

  static FrameMetadata frame(CameraIntrinsics k) {
    return new FrameMetadata(
        0,
        k.imageFrame(),
        TIME,
        Optional.empty(),
        k.widthPixels(),
        k.heightPixels(),
        Optional.of(ID));
  }

  static FrameMetadata frame() {
    return frame(intrinsics());
  }

  static PixelPoint pixel(double u, double v) {
    return new PixelPoint(I, u, v);
  }

  static Vector3 camera(double x, double y, double z) {
    return new Vector3(C, x, y, z);
  }

  static FrameId image(String id) {
    return new FrameId(FrameKind.IMAGE, id);
  }
}
