# Episode lifecycle

IMPLEMENTED: one compact mutable internal episode per WorldEntityId; external contracts stay frozen. Episode ID combines session, entity serial and start nanoseconds. Event IDs add action, level and repeat generation; no per-frame UUID. Silence retains event identity instead of creating a new event each update.

Episode tracks start, last seen, previous level, highest announced level, last intent time, repeat count, continuity and current event. Disappearance or gated evidence closes active relevance. A short return retains suppression history; a return after reappearance_ns starts a new episode. History expires after history_retention_ns, with deterministic bounded eviction (current IDs first, then most recently seen, then ID).

New session resets all state. An explicit reset is required on backward seek; out-of-order input raises before state mutation. Same timestamp is consumed once even if a caller resubmits altered content, producing DUPLICATE_STATE silence. now_ns must be authoritative observation/state time, not wall-clock time.

LIMITATION: tracker ID switches can create duplicate episodes; the engine never merges identities or suppresses across physical objects. This trades duplicates for avoiding incorrect cross-object suppression.
