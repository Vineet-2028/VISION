# ADR-004: Opt-in bounded encrypted event history

Status: accepted for the local Product V1.1 implementation.

## Context

Preserve the frozen Alpha engine while improving product usability and the private
data foundation. The supplied target architecture is a proposal, not evidence.

## Decision

Use native SQLite and Android Keystore AES-GCM payloads, not a new Room layer. Limit detailed records to seven days, summaries to selected 1/7/30/90-day retention and total storage to 1000 rows/8 MiB.

## Consequences and acceptance

Timestamp indexes remain plaintext. Deletion of local rows does not erase exported files, flash remnants or research assets. Device migration/reinstall tests remain a gate.

See the Product V1.1 release checklist for executed verification and open gates.
