package dev.sentinel.guardian;

import java.util.Objects;

/**
 * Synchronized raw accelerometer specific force (gravity NOT compensated) and gyro. At rest in z-up
 * DEVICE coordinates an ideal accelerometer measures +g on z. Hardware adapters must map sensor
 * signs/axes before constructing this contract.
 */
public final class ImuSample implements TimedObservation {
  private final MonotonicTime time;
  private final Vector3 rawSpecificForceMps2;
  private final Vector3 angularVelocityRadiansPerSecond;

  public ImuSample(
      MonotonicTime time, Vector3 rawSpecificForceMps2, Vector3 angularVelocityRadiansPerSecond) {
    this.time = Objects.requireNonNull(time, "time");
    rawSpecificForceMps2.frame().requireSame(angularVelocityRadiansPerSecond.frame());
    this.rawSpecificForceMps2 = rawSpecificForceMps2;
    this.angularVelocityRadiansPerSecond = angularVelocityRadiansPerSecond;
  }

  public MonotonicTime time() {
    return time;
  }

  public Vector3 rawSpecificForceMps2() {
    return rawSpecificForceMps2;
  }

  public Vector3 angularVelocityRadiansPerSecond() {
    return angularVelocityRadiansPerSecond;
  }
}
