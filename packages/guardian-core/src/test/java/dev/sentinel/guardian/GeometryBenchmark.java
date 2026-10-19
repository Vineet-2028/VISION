package dev.sentinel.guardian;

/** Opt-in synthetic desktop diagnostic; not a unit test or mobile performance claim. */
public final class GeometryBenchmark {
  private GeometryBenchmark() {}

  private static double run(int count) {
    CameraModel model =
        GeometryFixtures.model(
            GeometryFixtures.intrinsics(), new BrownConradyDistortion(.1, .01, 0, .001, -.002, 1));
    FrameMetadata frame = GeometryFixtures.frame();
    double checksum = 0;
    for (int i = 0; i < count; i++) {
      Vector3 ray =
          model
              .pixelToCameraRay(GeometryFixtures.pixel(100 + i % 800, 200 + i % 600), frame)
              .orElseThrow(() -> new IllegalStateException("Synthetic ray unavailable"));
      checksum += ray.x() + ray.y() + ray.z();
    }
    return checksum;
  }

  public static void main(String[] args) {
    double warmup = run(100000);
    long start = System.nanoTime();
    double checksum = run(1000000);
    long elapsed = System.nanoTime() - start;
    System.out.println(
        "Diagnostic only: ns/ray="
            + elapsed / 1000000.0
            + ", checksum="
            + checksum
            + ", warmup="
            + warmup);
  }
}
