# AlertPresentation

IMPLEMENTED: speech_text, short_text, priority, style, modality recommendations, source/attention/generation timestamps, nullable source age, attention age, deadline, quality, timing status, word/character counts, estimated duration and template provenance. No mutable speech object.

READY means text sink acceptance, not playback or perception by a user. NO_PRESENTATION includes attention silence and null sink. DROPPED_EXPIRED, DROPPED_INVALID, DROPPED_DUPLICATE, DROPPED_SUPERSEDED and UNRENDERABLE explain failed attempts. Silence never produces an all-clear message.

RecordingAlertPresenter has one latest pending text slot, bounded 128-entry default history and ID ledger. New accepted attention-selected output supersedes the pending text; it does not rank candidates. A monotonic timestamp watermark rejects replayed old decisions after ID eviction. Equal timestamps may not create another delivery. Wrong sessions require explicit reset. take(now_ns) checks expiry again; a future real audio sink must do the same immediately before playback.

English is the only V1 language. Repeat uses the full standalone phrase; escalation changes emphasis metadata, not factual content. Alternate renderers must preserve evidence and safety constraints.

AlertOutput also records sink acceptance time, source age at acceptance, presentation age and the superseded alert ID. These are text delivery diagnostics, not playback measurements. The pending consumer rechecks expiry and updates delivery age at take().
