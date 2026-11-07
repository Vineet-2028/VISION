# ADR-002: Pinned local wireless transport

Status: accepted for the local Product V1.1 implementation.

## Context

Preserve the frozen Alpha engine while improving product usability and the private
data foundation. The supplied target architecture is a proposal, not evidence.

## Decision

Use same-LAN TLS, a physically verified QR certificate, a 120-second single-use code and scoped rotating session grants. Keep loopback operator controls. Defer mDNS.

## Consequences and acceptance

Windows remains necessary. Gateway restart requires re-pairing; physical Wi-Fi, certificate and Bluetooth acceptance is still pending.

See the Product V1.1 release checklist for executed verification and open gates.
