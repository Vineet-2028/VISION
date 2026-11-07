# ADR-007: Versioned consent-aware offline datasets

Status: accepted for the local Product V1.1 implementation.

## Context

Preserve the frozen Alpha engine while improving product usability and the private
data foundation. The supplied target architecture is a proposal, not evidence.

## Decision

Require separate current research consent, reviewed provenance, canonical hash-bound versions and connected participant/route/session split groups. Persist withdrawal before deleting objects.

## Consequences and acceptance

Exported manifests are snapshots. Downstream consumers must check the registry and current consent, and may not use stale exports after withdrawal.

See the Product V1.1 release checklist for executed verification and open gates.
