package dev.sentinel.guardian;

/** Opt-in desktop diagnostic only. No wall-clock assertions or benchmark claims. */
public final class MathBenchmark {
  private MathBenchmark() {}

  private static double run(int count) {
    FrameId frame = new FrameId(FrameKind.LOCAL_WORLD, "benchmark");
    Vector3 velocity = new Vector3(frame, -2, .1, 0);
    double checksum = 0;
    for (int i = 0; i < count; i++) {
      CpaResult result = Motion.closestApproach(new Vector3(frame, 10 + (i % 97), 2, 0), velocity);
      checksum += result.distanceMeters().getAsDouble();
    }
    return checksum;
  }

  public static void main(String[] args) {
    double warmup = run(100000);
    long start = System.nanoTime();
    double checksum = run(1000000);
    long elapsed = System.nanoTime() - start;
    System.out.println(
        "Diagnostic only: ns/operation="
            + elapsed / 1000000.0
            + ", checksum="
            + checksum
            + ", warmup="
            + warmup);
  }
}
