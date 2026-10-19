package dev.sentinel.guardian;

import java.util.OptionalDouble;

/** Single-owner scalar spike filter. Unavailable until three samples; cadence is caller-owned. */
public final class Median3Filter {
  private final double[] values = new double[3];
  private int count, index;

  public OptionalDouble update(double value) {
    values[index] = NumericPolicy.finite(value);
    index = (index + 1) % 3;
    count = StrictMath.min(3, count + 1);
    if (count < 3) return OptionalDouble.empty();
    double a = values[0], b = values[1], c = values[2];
    return OptionalDouble.of(
        StrictMath.max(StrictMath.min(a, b), StrictMath.min(StrictMath.max(a, b), c)));
  }

  public void reset() {
    count = 0;
    index = 0;
    java.util.Arrays.fill(values, 0);
  }
}
