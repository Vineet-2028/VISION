package dev.sentinel.guardian;

/** Single-owner bounded DEVICE->WORLD history; reset on frame/session discontinuity. */
public final class PoseHistory {
  private final SampleBuffer<DevicePoseEstimate> samples;
  private FrameId device, world;

  public PoseHistory(int capacity, long retentionNanos, long lateWindowNanos) {
    samples = new SampleBuffer<>(capacity, retentionNanos, lateWindowNanos);
  }

  public SampleBuffer.Insertion add(DevicePoseEstimate pose) {
    if (pose.transform().isPresent() && device != null && world != null) {
      device.requireSame(pose.transform().get().from());
      world.requireSame(pose.transform().get().to());
    }
    SampleBuffer.Insertion status = samples.add(pose);
    if ((status == SampleBuffer.Insertion.ACCEPTED
            || status == SampleBuffer.Insertion.ACCEPT_AND_REORDER)
        && pose.transform().isPresent()) {
      device = pose.transform().get().from();
      world = pose.transform().get().to();
    }
    return status;
  }

  public TemporalAlignment<DevicePoseEstimate> at(
      MonotonicTime time, SynchronizationPolicy policy) {
    return TemporalLookup.lookup(
        samples, time, policy, p -> p.transform().isPresent(), Interpolation::pose);
  }

  public int size() {
    return samples.size();
  }

  public void reset() {
    samples.reset();
    device = null;
    world = null;
  }
}
