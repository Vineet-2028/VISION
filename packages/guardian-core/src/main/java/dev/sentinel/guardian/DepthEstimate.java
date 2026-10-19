package dev.sentinel.guardian;

import java.util.Objects;
import java.util.OptionalDouble;

/** Metric range is Euclidean distance from camera center, NOT optical-axis z-depth. */
public final class DepthEstimate {
  public enum Scale {
    METRIC_RANGE,
    RELATIVE
  }

  private final Scale scale;
  private final ScalarEstimate estimate;
  private final String source;

  private DepthEstimate(Scale scale, ScalarEstimate estimate, String source) {
    this.scale = Objects.requireNonNull(scale, "scale");
    this.estimate = Objects.requireNonNull(estimate, "estimate");
    this.source = NumericPolicy.identity(source);
    if (scale == Scale.METRIC_RANGE
        && estimate.value().isPresent()
        && estimate.value().getAsDouble() <= 0) {
      throw new IllegalArgumentException("Metric range must be positive");
    }
  }

  public static DepthEstimate metricRange(
      double meters, OptionalDouble stdMeters, Confidence confidence, String source) {
    return new DepthEstimate(
        Scale.METRIC_RANGE, ScalarEstimate.known(meters, stdMeters, confidence), source);
  }

  /** Producer-defined relative values may be signed; source must specify ordering and scale. */
  public static DepthEstimate relative(
      double value, OptionalDouble std, Confidence confidence, String source) {
    return new DepthEstimate(Scale.RELATIVE, ScalarEstimate.known(value, std, confidence), source);
  }

  public static DepthEstimate unknown(Scale scale, String source) {
    return new DepthEstimate(scale, ScalarEstimate.unknown(), source);
  }

  public OptionalDouble meters() {
    return scale == Scale.METRIC_RANGE ? estimate.value() : OptionalDouble.empty();
  }

  public Scale scale() {
    return scale;
  }

  public ScalarEstimate estimate() {
    return estimate;
  }

  public String source() {
    return source;
  }
}
