package dev.sentinel.guardian;

/** Adapter-supplied measurement, delivery, processing start/end times in one mapped clock. */
public final class ProcessingTiming {
  private final MonotonicTime capture, delivery, start, end;

  public ProcessingTiming(
      MonotonicTime capture, MonotonicTime delivery, MonotonicTime start, MonotonicTime end) {
    delivery.elapsedNanosSince(capture);
    start.elapsedNanosSince(delivery);
    end.elapsedNanosSince(start);
    this.capture = capture;
    this.delivery = delivery;
    this.start = start;
    this.end = end;
  }

  public MonotonicTime capture() {
    return capture;
  }

  public MonotonicTime delivery() {
    return delivery;
  }

  public MonotonicTime processingStart() {
    return start;
  }

  public MonotonicTime processingEnd() {
    return end;
  }

  public long deliveryLatencyNanos() {
    return delivery.elapsedNanosSince(capture);
  }

  public long captureToProcessingNanos() {
    return start.elapsedNanosSince(capture);
  }

  public long processingDurationNanos() {
    return end.elapsedNanosSince(start);
  }

  public long captureToEndNanos() {
    return end.elapsedNanosSince(capture);
  }
}
