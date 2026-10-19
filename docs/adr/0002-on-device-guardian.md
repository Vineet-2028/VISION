# ADR 0002: Guardian critical decisions remain on-device

Status: accepted architectural direction; mobile implementation deferred.

## Context

Hazard response must work without connectivity. The current Spring Boot and web
foundation cannot provide a bounded-latency offline assistive runtime.

## Decision

Guardian's critical runtime will run on-device. Spring Boot owns control-plane
and optional cloud services. Web owns configuration, monitoring and dashboard
infrastructure. Neither server availability nor an LLM may gate critical hazard
decisions. Android/native mobile will be restored in a later task; Task 002 adds
no Android code.

The Java core compiles against Java 8 APIs using the existing JDK 21 toolchain,
with no production dependencies. Android API availability/desugaring and device
numerics must be tested when that runtime is selected. This is source portability,
not an assertion that an Android application has already been built.

Inference runtime/model selection will follow reproducible latency, recall, memory,
power and thermal benchmarks. There is no runtime/model commitment in this ADR.

## Consequences

The critical local loop continues without network. Cloud/explore features may be
unavailable offline and must not stall or override local safety processing.
Adapters own capture, synchronization, calibration and presentation. Core algorithms
remain deterministic and reusable in replay, simulation and backend analysis.
No component is permitted to claim safety without evaluation.
