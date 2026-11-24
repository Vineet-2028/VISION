# Task017 audit

Pre-task READ-ONLY inspection: AttentionDecision/Event/Set, reasons, episode identity, risk contracts, WorldEntity category/bearing, InteractionAnalysis, source timestamps, scheduler, recording, overlays, replay, component replacement contracts and Task016 report. Existing components did not own final alert wording. No new inference dependency is necessary. Mutable presenter state is single-owner.

Contract gaps: no authorized category/direction or original evidence timestamp in AttentionDecision. Additive optional semantic evidence, source timestamp/basis and physical-validity fields preserve old construction defaults. Current risk ages pass through attention without recomputing geometry. Existing real producer does not invent semantic facts. Source-age gaps remain explicit. No Tasks001–016 rewrite.

Read-only adversarial pass followed by targeted fixes: named audio parameter preserves injected engine compatibility; expired output is checked again after renderer and before consumption; bounded ID eviction retains a timestamp watermark; wrong session requires reset; all cleanup paths retain recorder closure. Regression tests cover these boundaries. New files have no LLM/network/telemetry imports or model dependencies.

CRITICAL/HIGH: see final research report for final executed status. MEDIUM: unknown wording usefulness, low source coverage, slow upstream processing, no speech/human/hardware validation, limited current semantics. LOW: English-only vocabulary and generic fallback reduce demonstration richness but avoid unsupported claims. No human review is marked complete.

Final executed verification: 1222 tests and `npm.cmd run verify` passed. Post-run archive-reader schema rejection was checked directly and Ruff passed. Two paired timings disagree strongly (+20.43%, -68.27%); causal full-pipeline overhead remains inconclusive. See the Task017 report for measurements, chronological run scope and all remaining unverified items.
