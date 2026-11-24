# AlertIntent

IMPLEMENTED frozen dataclass in `apps/perception-lab/src/perception_lab/alert_types.py`. Fields: deterministic alert/event/episode/session IDs, attention timestamp, nullable original source observation timestamp, entity, decision type, category, direction, interaction, ordinal urgency, source risk, quality, physical-validity label, deadline, reasons, compact provenance, configuration hash and presentation constraints.

IDs include session plus AttentionEvent.event_id; no random identity is introduced. Risk/attention component references, episode/entity IDs and frame records permit upstream correlation. There is no duplicated risk assessment or physical computation.

Source age basis is explicit: OLDEST_REPORTED_EVIDENCE, RISK_STATE_ONLY or UNAVAILABLE. Missing original observations remain null. The oldest reported nonnegative evidence age is retained by AttentionEngine; this is not a claim that every upstream source supplied its age. Existing schema11 archived attention has no original source timestamp and remains unavailable when replayed.

Semantic evidence may authorize category/direction/interaction only with same entity/session, a valid observation interval, acceptable evidence quality and component provenance. Current real policy leaves it absent. Typed fixture semantics test future boundary behavior, not accuracy.
