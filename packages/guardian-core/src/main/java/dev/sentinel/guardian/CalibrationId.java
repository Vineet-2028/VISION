package dev.sentinel.guardian;

/** Version includes effective image geometry, lens and stabilization configuration. */
public final class CalibrationId {
  private final String cameraId;
  private final String version;

  public CalibrationId(String cameraId, String version) {
    this.cameraId = NumericPolicy.identity(cameraId);
    this.version = NumericPolicy.identity(version);
  }

  @Override
  public boolean equals(Object other) {
    if (!(other instanceof CalibrationId)) return false;
    CalibrationId id = (CalibrationId) other;
    return cameraId.equals(id.cameraId) && version.equals(id.version);
  }

  @Override
  public int hashCode() {
    return 31 * cameraId.hashCode() + version.hashCode();
  }

  public void requireSame(CalibrationId other) {
    if (!equals(other)) throw new IllegalArgumentException("Calibration identity mismatch");
  }

  public String cameraId() {
    return cameraId;
  }

  public String version() {
    return version;
  }
}
