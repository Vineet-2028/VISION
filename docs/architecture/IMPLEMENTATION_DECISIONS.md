# Product V1.1 implementation decisions

The supplied `VISION_TARGET_ARCHITECTURE_V2.md` is a proposal, preserved verbatim.
Its release gates are not statements of implemented behavior. The working branch
is `codex/product-v1-1`. Pre-existing work was dirty; its tracked diff was saved
in `benchmark-results/v02/product-v1-1-preexisting.patch` before this pass.

Frozen engine manifest SHA-256:
`ecd83215cc8f8e144ec9126b61415e8ca38b854a4126cfdbc6e52d55affa6254`.
No measured inference, model or original benchmark changes are authorized here.

| Plane / component                | Real implementation                             | Decision                                                                  |
| -------------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------- |
| Runtime / Guardian               | `packages/guardian-core`, `apps/perception-lab` | Existing; preserve frozen runtime                                         |
| Field wire contract              | `field_protocol.py`, `FieldTransport.kt`        | Existing V1 framing/clock/expiry; extend authentication outside inference |
| Public product                   | `apps/web/src/app`                              | Modify landing/demo; no public filesystem/media API                       |
| Private Lab                      | existing replay/review/live/session components  | New authenticated `/lab`; reuse components and exact replay               |
| Static distribution              | Next static export                              | New allowlisted build, excluding private routes and runtime               |
| Wi-Fi pairing                    | gateway TLS + Android transport                 | Modify: pinned TLS, single-use bootstrap and revocable scoped grants      |
| Event history                    | Android app-private storage                     | New encrypted SQLite records, independent of runtime queues               |
| Feedback / consent               | product and offline dataset contracts           | New; service use is not training consent                                  |
| Dataset version / review / split | Python offline modules                          | New; reject pseudo-labels as independent review, group-separated splits   |
| Object storage                   | local adapter                                   | New local default; remote upload disabled without explicit configuration  |
| Optional ranking                 | offline evaluation                              | New shadow experiment contract; no training or live policy mutation       |
| Cloud history sync / BFF         | Spring API remains existing                     | Deferred: no account or multi-device requirement yet                      |
| mDNS                             | manual endpoint / QR                            | Deferred: QR carries endpoint; avoid discovery dependency                 |
| Mobile inference                 | Android captures, Windows executes              | Deferred Task019; marketing hosting cannot supply inference               |
| Physical Bluetooth / Wi-Fi tests | real phone required                             | External gate, not satisfied by software tests                            |

Conceptual FrameEnvelope.v2 maps to the existing VISION_FIELD_PROTOCOL_V1 header;
no incompatible replacement schema is introduced. GuardianDecision stays with
the qualified runtime. Product history and research annotations cannot mutate it.

## Decision records

- [ADR-001-runtime-vs-product-vs-learning](adr/ADR-001-runtime-vs-product-vs-learning.md)
- [ADR-002-wireless-local-first](adr/ADR-002-wireless-local-first.md)
- [ADR-003-public-demo-data-policy](adr/ADR-003-public-demo-data-policy.md)
- [ADR-004-history-retention-deletion](adr/ADR-004-history-retention-deletion.md)
- [ADR-005-image-temporal-model-boundary](adr/ADR-005-image-temporal-model-boundary.md)
- [ADR-006-alert-usefulness-and-no-online-RL](adr/ADR-006-alert-usefulness-and-no-online-RL.md)
- [ADR-007-consent-and-data-versioning](adr/ADR-007-consent-and-data-versioning.md)
- [ADR-008-cloud-cost-gates](adr/ADR-008-cloud-cost-gates.md)
- [ADR-009-mobile-inference-roadmap](adr/ADR-009-mobile-inference-roadmap.md)
