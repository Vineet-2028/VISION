package dev.sentinel.guardian;

import static dev.sentinel.guardian.TemporalFixtures.*;
import static org.junit.jupiter.api.Assertions.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class FilteringTest {
  @Test
  void failedInitializationDoesNotPoisonFilter() {
    LowPassFilter f = new LowPassFilter(1, 100);
    assertThrows(NullPointerException.class, () -> f.update(world(99, 0, 0), null));
    assertEquals(2, f.update(world(2, 0, 0), time(1)).get().x());
  }

  @Test
  void lowPassStepWithIrregularTimeAndReset() {
    LowPassFilter f = new LowPassFilter(1 / (2 * StrictMath.PI), 10000000000L);
    assertEquals(0, f.update(world(0, 0, 0), time(0)).get().x());
    assertEquals(5, f.update(world(10, 0, 0), time(1000000000)).get().x(), 1e-12);
    assertEquals(8.75, f.update(world(10, 0, 0), time(4000000000L)).get().x(), 1e-12);
    f.reset();
    assertEquals(20, f.update(world(20, 0, 0), time(0)).get().x());
  }

  @Test
  void rejectedFilterInputsDoNotMutateAndGapsReset() {
    LowPassFilter f = new LowPassFilter(1 / (2 * StrictMath.PI), 1000000000);
    f.update(world(0, 0, 0), time(0));
    assertThrows(IllegalArgumentException.class, () -> f.update(world(100, 0, 0), time(0)));
    assertThrows(
        IllegalArgumentException.class, () -> f.update(device(100, 0, 0), time(1000000000)));
    assertThrows(
        IllegalArgumentException.class,
        () -> f.update(world(100, 0, 0), new MonotonicTime("other", 1)));
    assertEquals(5, f.update(world(10, 0, 0), time(1000000000)).get().x(), 1e-12);
    assertFalse(f.update(world(20, 0, 0), time(3000000000L)).isPresent());
    assertEquals(25, f.update(world(30, 0, 0), time(4000000000L)).get().x(), 1e-12);
  }

  @Test
  void seededFiltersRemainFiniteAndBetweenEndpoints() {
    Random r = new Random(406);
    LowPassFilter f = new LowPassFilter(4, 1000000000);
    long t = 0;
    double previous = f.update(world(0, 0, 0), time(t)).get().x();
    for (int i = 0; i < 1000; i++) {
      t += 1000 + r.nextInt(1000000);
      double x = r.nextGaussian() * 1e100;
      double y = f.update(world(x, 0, 0), time(t)).get().x();
      assertTrue(Double.isFinite(y));
      assertTrue(y >= StrictMath.min(previous, x) && y <= StrictMath.max(previous, x));
      previous = y;
    }
    assertThrows(IllegalArgumentException.class, () -> new LowPassFilter(Double.NaN, 10));
    assertThrows(IllegalArgumentException.class, () -> new LowPassFilter(0, 10));
  }

  @Test
  void medianSpikeAndReset() {
    Median3Filter f = new Median3Filter();
    assertFalse(f.update(1).isPresent());
    assertFalse(f.update(1000).isPresent());
    assertEquals(2, f.update(2).getAsDouble());
    assertEquals(3, f.update(3).getAsDouble());
    f.reset();
    assertFalse(f.update(9).isPresent());
    assertThrows(IllegalArgumentException.class, () -> f.update(Double.POSITIVE_INFINITY));
  }

  @Test
  void statisticsLargeOffsetAndTransactionalOverflow() {
    Statistics s = new Statistics();
    s.add(1e12 + 1);
    s.add(1e12 + 2);
    s.add(1e12 + 3);
    assertEquals(1e12 + 2, s.mean());
    assertEquals(2.0 / 3, s.populationVariance(), 1e-12);
    assertThrows(IllegalArgumentException.class, () -> s.add(Double.NaN));
    assertEquals(3, s.count());
    s.reset();
    s.add(Double.MAX_VALUE);
    assertThrows(IllegalArgumentException.class, () -> s.add(-Double.MAX_VALUE));
    assertEquals(1, s.count());
    s.reset();
    assertThrows(IllegalStateException.class, s::mean);
  }

  @Test
  void absoluteOutlierGates() {
    assertTrue(OutlierGate.accepts(10, 12, 2));
    assertFalse(OutlierGate.accepts(10, 12.1, 2));
    assertFalse(OutlierGate.accepts(-Double.MAX_VALUE, Double.MAX_VALUE, Double.MAX_VALUE));
    assertTrue(OutlierGate.accepts(world(0, 0, 0), world(3, 4, 0), 5));
    assertFalse(OutlierGate.accepts(world(0, 0, 0), world(3, 4, 0), 4.9));
    assertThrows(
        IllegalArgumentException.class,
        () -> OutlierGate.accepts(world(0, 0, 0), device(0, 0, 0), 1));
  }

  private static List<ImuSample> window(double g, double gyro) {
    List<ImuSample> samples = new ArrayList<>();
    for (int i = 0; i < 5; i++)
      samples.add(new ImuSample(time(i * 10000000L), device(0, 0, g), device(0, 0, gyro)));
    return samples;
  }

  @Test
  void stationaryRotatingAcceleratingAndInsufficientWindows() {
    StationaryDetectionPolicy p =
        new StationaryDetectionPolicy(4, 30000000, 20000000, .05, 9.80665, .1, .001);
    assertEquals(
        StationaryDetector.Result.STATIONARY_CANDIDATE,
        StationaryDetector.evaluate(window(9.80665, 0), p));
    assertEquals(
        StationaryDetector.Result.MOVING, StationaryDetector.evaluate(window(9.80665, .2), p));
    assertEquals(StationaryDetector.Result.MOVING, StationaryDetector.evaluate(window(11, 0), p));
    assertEquals(
        StationaryDetector.Result.INSUFFICIENT_DATA,
        StationaryDetector.evaluate(window(9.80665, 0).subList(0, 2), p));
    List<ImuSample> gapped = window(9.80665, 0);
    gapped.set(4, new ImuSample(time(100000000), device(0, 0, 9.80665), device(0, 0, 0)));
    assertEquals(
        StationaryDetector.Result.INSUFFICIENT_DATA, StationaryDetector.evaluate(gapped, p));
  }

  @Test
  void forceVarianceAndNonmonotonicWindow() {
    List<ImuSample> samples = window(9.8, 0);
    samples.set(2, new ImuSample(time(20000000), device(0, 0, 10), device(0, 0, 0)));
    assertEquals(
        StationaryDetector.Result.MOVING,
        StationaryDetector.evaluate(
            samples, new StationaryDetectionPolicy(4, 30000000, 20000000, .05, 9.8, 1, .001)));
    samples.set(3, samples.get(2));
    assertThrows(
        IllegalArgumentException.class,
        () ->
            StationaryDetector.evaluate(
                samples, new StationaryDetectionPolicy(4, 30000000, 20000000, .05, 9.8, 1, 1)));
  }
}
