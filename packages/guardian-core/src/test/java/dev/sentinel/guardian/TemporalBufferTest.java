package dev.sentinel.guardian;

import static dev.sentinel.guardian.TemporalFixtures.*;
import static org.junit.jupiter.api.Assertions.*;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class TemporalBufferTest {
  @Test
  void largeGapEvictsWholePrefixAndPreservesBoundary() {
    SampleBuffer<AngularVelocitySample> b = new SampleBuffer<>(1000, 1000, 1000);
    for (int i = 0; i < 1000; i++) b.add(gyro(i, 0));
    b.add(gyro(1999, 0));
    assertEquals(2, b.size());
    assertEquals(999, b.snapshot().get(0).time().nanos());
    b.add(gyro(3000, 0));
    assertEquals(1, b.size());
    assertEquals(3000, b.snapshot().get(0).time().nanos());
  }

  @Test
  void durationsAndLargeTimestamps() {
    assertEquals(0, Temporal.durationSeconds(time(2), time(2)));
    assertEquals(1e-9, Temporal.durationSeconds(time(Long.MAX_VALUE - 1), time(Long.MAX_VALUE)));
    assertEquals(
        Long.MAX_VALUE - 1,
        Temporal.midpoint(time(Long.MAX_VALUE - 2), time(Long.MAX_VALUE)).nanos());
    assertThrows(IllegalArgumentException.class, () -> Temporal.durationSeconds(time(2), time(1)));
    assertThrows(
        IllegalArgumentException.class,
        () -> Temporal.durationSeconds(time(0), new MonotonicTime("other", 1)));
    assertThrows(IllegalArgumentException.class, () -> time(999).motionSecondsSince(time(0)));
  }

  @Test
  void clockMappingChecksSignedOverflowAndIdentity() {
    assertEquals(20, new ClockMapping("timing-clock", "camera", 10).map(time(10)).get().nanos());
    assertEquals(
        "camera", new ClockMapping("timing-clock", "camera", -10).map(time(10)).get().clockId());
    assertFalse(new ClockMapping("timing-clock", "camera", -11).map(time(10)).isPresent());
    assertFalse(
        new ClockMapping("timing-clock", "camera", 1).map(time(Long.MAX_VALUE)).isPresent());
    assertThrows(
        IllegalArgumentException.class,
        () -> new ClockMapping("timing-clock", "camera", 1).map(new MonotonicTime("x", 0)));
    assertThrows(IllegalArgumentException.class, () -> new ClockMapping("a", "a", 0));
  }

  @Test
  void ageIsExplicitAndThresholdInclusive() {
    assertEquals(Temporal.Age.FRESH, Temporal.age(time(10), time(5), 5, true));
    assertEquals(Temporal.Age.STALE, Temporal.age(time(11), time(5), 5, true));
    assertEquals(Temporal.Age.FUTURE, Temporal.age(time(1), time(5), 5, true));
    assertEquals(Temporal.Age.INVALID, Temporal.age(time(10), time(5), 5, false));
    assertThrows(IllegalArgumentException.class, () -> Temporal.age(time(10), time(5), -1, true));
  }

  @Test
  void emptyDuplicateOrderedLookupAndTie() {
    SampleBuffer<AngularVelocitySample> b = new SampleBuffer<>(3, 100, 100);
    assertFalse(b.nearest(time(0)).isPresent());
    assertFalse(b.atOrBefore(time(0)).isPresent());
    assertFalse(b.atOrAfter(time(0)).isPresent());
    assertEquals(SampleBuffer.Insertion.ACCEPTED, b.add(gyro(10, 1)));
    assertEquals(SampleBuffer.Insertion.ACCEPTED, b.add(gyro(30, 3)));
    assertEquals(SampleBuffer.Insertion.ACCEPT_AND_REORDER, b.add(gyro(20, 2)));
    assertEquals(SampleBuffer.Insertion.DUPLICATE, b.add(gyro(20, 99)));
    assertEquals(2, b.nearest(time(20)).get().radiansPerSecond().z());
    assertEquals(20, b.nearest(time(25)).get().time().nanos());
    assertEquals(20, b.atOrBefore(time(21)).get().time().nanos());
    assertEquals(30, b.atOrAfter(time(21)).get().time().nanos());
    assertFalse(b.atOrBefore(time(9)).isPresent());
    assertFalse(b.atOrAfter(time(31)).isPresent());
  }

  @Test
  void evictionLateWindowAndSnapshotIsolation() {
    SampleBuffer<AngularVelocitySample> b = new SampleBuffer<>(3, 20, 5);
    b.add(gyro(10, 0));
    b.add(gyro(20, 0));
    assertEquals(SampleBuffer.Insertion.REJECT_TOO_LATE, b.add(gyro(14, 0)));
    assertEquals(SampleBuffer.Insertion.ACCEPT_AND_REORDER, b.add(gyro(15, 0)));
    assertEquals(SampleBuffer.Insertion.OUTSIDE_BUFFER, b.add(gyro(9, 0)));
    List<AngularVelocitySample> snapshot = b.snapshot();
    assertThrows(UnsupportedOperationException.class, () -> snapshot.clear());
    b.add(gyro(50, 0));
    assertEquals(1, b.size());
    assertEquals(3, snapshot.size());
    assertEquals(SampleBuffer.Insertion.OUTSIDE_BUFFER, b.add(gyro(20, 0)));
    assertThrows(
        IllegalArgumentException.class,
        () -> b.add(new AngularVelocitySample(new MonotonicTime("new", 51), device(0, 0, 0))));
    b.reset();
    assertEquals(0, b.size());
    b.add(new AngularVelocitySample(new MonotonicTime("new", 1), device(0, 0, 0)));
  }

  @Test
  void randomizedOrderingAndLateFloodStayBounded() {
    SampleBuffer<AngularVelocitySample> b = new SampleBuffer<>(32, 1000, 1000);
    List<Integer> order = new ArrayList<>();
    for (int i = 0; i < 500; i++) order.add(i);
    Collections.shuffle(order, new Random(402));
    for (int t : order) {
      b.add(gyro(t, 0));
      assertTrue(b.size() <= 32);
      List<AngularVelocitySample> s = b.snapshot();
      for (int i = 1; i < s.size(); i++)
        assertTrue(s.get(i - 1).time().nanos() < s.get(i).time().nanos());
    }
    for (int i = 0; i < 10000; i++) b.add(gyro(0, 0));
    assertTrue(b.size() <= 32);
  }

  @Test
  void timingJitterGapsAndLatency() {
    TimingMetrics m = new TimingMetrics();
    m.add(time(0));
    m.add(time(1000000000));
    m.add(time(3000000000L));
    m.add(time(6000000000L));
    assertEquals(3, m.intervalCount());
    assertEquals(2, m.meanSeconds());
    assertEquals(StrictMath.sqrt(2.0 / 3), m.standardDeviationSeconds(), 1e-12);
    assertEquals(1, m.minSeconds());
    assertEquals(3, m.maxSeconds());
    assertTrue(TimingMetrics.gap(time(0), time(30), 10, 2).exceedsConfiguredRatio());
    assertEquals(3, TimingMetrics.gap(time(0), time(30), 10, 2).ratio());
    assertThrows(IllegalArgumentException.class, () -> m.add(time(6000000000L)));
    m.reset();
    assertEquals(0, m.intervalCount());
    ProcessingTiming p = new ProcessingTiming(time(10), time(15), time(20), time(30));
    assertEquals(5, p.deliveryLatencyNanos());
    assertEquals(10, p.captureToProcessingNanos());
    assertEquals(10, p.processingDurationNanos());
    assertEquals(20, p.captureToEndNanos());
    assertThrows(
        IllegalArgumentException.class,
        () -> new ProcessingTiming(time(10), time(9), time(20), time(30)));
  }
}
