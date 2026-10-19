package dev.sentinel.guardian;

/** Opt-in desktop diagnostic only; no timing assertions or device latency claim. */
public final class TemporalBenchmark {
  private TemporalBenchmark() {}

  private static double run(int count) {
    PoseHistory history = new PoseHistory(256, 1000000000, 1000000);
    SynchronizationPolicy policy = new SynchronizationPolicy(10000000, 0, false, false);
    double checksum = 0;
    for (int i = 0; i < count; i++) {
      history.add(TemporalFixtures.pose(i * 1000000L, i, Quaternion.identity()));
      if (i > 0)
        checksum +=
            history
                .at(TemporalFixtures.time(i * 1000000L - 500000), policy)
                .value()
                .get()
                .transform()
                .get()
                .translationInToMeters()
                .x();
    }
    return checksum;
  }

  public static void main(String[] args) {
    double warmup = run(10000);
    long start = System.nanoTime();
    double checksum = run(100000);
    long elapsed = System.nanoTime() - start;
    System.out.println(
        "Diagnostic only: ns/insert+lookup="
            + elapsed / 100000.0
            + ", checksum="
            + checksum
            + ", warmup="
            + warmup);
  }
}
