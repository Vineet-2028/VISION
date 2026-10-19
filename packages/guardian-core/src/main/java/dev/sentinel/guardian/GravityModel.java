package dev.sentinel.guardian;

/** Configurable local gravity approximation, world z up. Nominal is not local calibration. */
public final class GravityModel {
  public static final double NOMINAL_MPS2 = 9.80665;
  private final Vector3 worldGravity;

  public GravityModel(FrameId world, double magnitude) {
    if (world.kind() != FrameKind.LOCAL_WORLD || NumericPolicy.finite(magnitude) <= 0)
      throw new IllegalArgumentException("Invalid world gravity");
    worldGravity = new Vector3(world, 0, 0, -magnitude);
  }

  public Vector3 worldGravity() {
    return worldGravity;
  }
}
