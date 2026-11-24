# Decisions and Task017 contract

IMPLEMENTED: frozen AttentionDecision includes timestamp, optional stable entity ID, SILENT/ANNOUNCE/REPEAT/ESCALATE, ordinal priority, source risk level, separate source quality, risk trend, reason codes, novelty, cooldown, repeat count, escalation flag, attention quality, event/episode identity, provenance and config hash. AttentionDecisionSet includes exactly one selected output, bounded suppressed records, scene status, reasons, expiry, risk provenance and inherited coverage.

Category and direction are nullable. RiskAssessment currently supplies neither authoritative category nor bearing; Task016 does not infer them. Interaction reasons pass through from the risk contract. Task017 must produce a generic semantic presentation when those optional fields are absent, rather than invent a class/direction. Adding an authoritative optional context contract later does not require vendor imports or risk internals.

All current qualified decisions remain DEGRADED. Unknown/gated outputs are UNAVAILABLE; neither state claims human or physical validation. Event validity is the minimum of risk-set expiry, per-assessment expiry and configured lifetime from the risk timestamp.

PLANNED: Task017 deterministic AlertIntent/AlertPresentation, audio/haptic rendering, delivery acknowledgement and actual playback priority. Not implemented here. No language or voice choices exist in Task016.
