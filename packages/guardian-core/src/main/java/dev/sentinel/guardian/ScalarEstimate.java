package dev.sentinel.guardian;

import java.util.Objects;
import java.util.OptionalDouble;

/** Scalar with optional one-standard-deviation uncertainty, in the scalar's own units. */
public final class ScalarEstimate {
  private final Validity validity;
  private final OptionalDouble value;
  private final OptionalDouble standardDeviation;
  private final Confidence confidence;

  private ScalarEstimate(
      Validity validity,
      OptionalDouble value,
      OptionalDouble standardDeviation,
      Confidence confidence) {
    this.validity = validity;
    this.value = value;
    this.standardDeviation = Objects.requireNonNull(standardDeviation, "standardDeviation");
    if (standardDeviation.isPresent()) NumericPolicy.nonNegative(standardDeviation.getAsDouble());
    this.confidence = Objects.requireNonNull(confidence, "confidence");
  }

  public static ScalarEstimate known(
      double value, OptionalDouble standardDeviation, Confidence confidence) {
    return new ScalarEstimate(
        Validity.KNOWN,
        OptionalDouble.of(NumericPolicy.finite(value)),
        standardDeviation,
        confidence);
  }

  public static ScalarEstimate unknown() {
    return new ScalarEstimate(
        Validity.UNKNOWN, OptionalDouble.empty(), OptionalDouble.empty(), new Confidence(0));
  }

  public Validity validity() {
    return validity;
  }

  public OptionalDouble value() {
    return value;
  }

  public OptionalDouble standardDeviation() {
    return standardDeviation;
  }

  public Confidence confidence() {
    return confidence;
  }
}
