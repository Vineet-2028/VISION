package dev.sentinel.guardian;

/** Azimuth (-pi,pi], elevation [-pi/2,pi/2]. Positive elevation is above optical horizon. */
public final class DirectionAngles {
  private final double azimuthRadians;
  private final double elevationRadians;

  public DirectionAngles(double azimuthRadians, double elevationRadians) {
    this.azimuthRadians = Angles.normalizeRadians(azimuthRadians);
    if (StrictMath.abs(NumericPolicy.finite(elevationRadians)) > StrictMath.PI / 2)
      throw new IllegalArgumentException("Invalid elevation");
    this.elevationRadians = elevationRadians;
  }

  public static DirectionAngles fromCameraDirection(Vector3 ray) {
    if (ray.frame().kind() != FrameKind.CAMERA)
      throw new IllegalArgumentException("Expected CAMERA frame");
    Vector3 direction = ray.normalized();
    double horizontal = StrictMath.hypot(direction.x(), direction.z());
    if (horizontal <= NumericPolicy.EPSILON)
      throw new IllegalArgumentException("Azimuth undefined at a pole");
    return new DirectionAngles(
        StrictMath.atan2(direction.x(), direction.z()),
        StrictMath.atan2(-direction.y(), horizontal));
  }

  public double azimuthRadians() {
    return azimuthRadians;
  }

  public double elevationRadians() {
    return elevationRadians;
  }
}
