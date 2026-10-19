package dev.sentinel.guardian;

/** Single-owner Welford accumulator. Finite failure is transactional; reset starts a new window. */
public final class Statistics {
  private long count;
  private double mean, m2, min, max;

  public void add(double value) {
    NumericPolicy.finite(value);
    if (count == Long.MAX_VALUE) throw new IllegalArgumentException("Sample count overflow");
    if (count == 0) {
      count = 1;
      mean = value;
      m2 = 0;
      min = value;
      max = value;
      return;
    }
    double delta = NumericPolicy.finite(value - mean);
    double nextMean = NumericPolicy.finite(mean + delta / (count + 1));
    double nextM2 = NumericPolicy.finite(m2 + delta * (value - nextMean));
    count++;
    mean = nextMean;
    m2 = StrictMath.max(0, nextM2);
    min = StrictMath.min(min, value);
    max = StrictMath.max(max, value);
  }

  private void requireData() {
    if (count == 0) throw new IllegalStateException("No observations");
  }

  public long count() {
    return count;
  }

  public double mean() {
    requireData();
    return mean;
  }

  public double populationVariance() {
    requireData();
    return m2 / count;
  }

  public double standardDeviation() {
    return StrictMath.sqrt(populationVariance());
  }

  public double min() {
    requireData();
    return min;
  }

  public double max() {
    requireData();
    return max;
  }

  public void reset() {
    count = 0;
    mean = 0;
    m2 = 0;
    min = 0;
    max = 0;
  }
}
