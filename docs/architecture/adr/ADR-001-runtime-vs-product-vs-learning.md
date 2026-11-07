# ADR-001: Separate runtime, product and learning

Status: accepted for the local Product V1.1 implementation.

## Context

Preserve the frozen Alpha engine while improving product usability and the private
data foundation. The supplied target architecture is a proposal, not evidence.

## Decision

The frozen Guardian stays authoritative. Product history and offline research consume projections and cannot modify its thresholds or source/model hashes.

## Consequences and acceptance

This preserves qualification evidence while allowing UI and storage evolution. Contract changes require explicit compatibility tests.

See the Product V1.1 release checklist for executed verification and open gates.
