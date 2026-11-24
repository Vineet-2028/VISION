# Architecture

IMPLEMENTED: optional deterministic AttentionEngine consumes only immutable RiskAssessmentSet and abstract AudioChannelState. Task017 consumes AttentionDecisionSet. No inference, geometry, risk recomputation, text generation, speech, navigation or external service. A single pipeline thread owns each engine.

Risk is evidence relevance; attention is interruption policy. Current output is an intent, not a delivery acknowledgement. Task017 must recheck validity immediately before presentation and report actual audio-busy state. Pipeline currently supplies IDLE because there is no audio subsystem.

O(N log N) ordering and bounded episode eviction; no pairwise entity geometry. Maximum 512 episode entries, 512 suppressed candidates per update, one selected output and max_interruptions+4 recent interruption records. There is no pending queue: fresh risk must justify any later candidate. Silent output is explicit even for an empty scene.

PROVISIONAL: balanced novelty/escalation is the primary candidate, subject to the measured report. No learned policy, spatial identity merging, clustering or personalization. UNKNOWN never means safe.

UNVALIDATED: human usefulness, physical risk, warning lead, target-device performance. Task014 tracker-proxy recall remains 5.8%. An attention policy cannot recover interactions never represented upstream.
