# Task016 attention — prototype completion report

Verified 2026-10-24. All attention labels remain draft; no production-safety qualification.

## A. PRE-TASK AUDIT

Read Task015 report/contracts, risk level/quality/trends, world identity/lifecycle/timestamps, Task014 quality/5.8% proxy recall, recording/scheduler, configuration, replacement contracts and verify task before edits. All seven requested stable input-boundary checks passed static inspection. No earlier attention owner or required risk-contract rewrite found. Existing Tasks009–015 uncommitted work preserved.

## B. FILES CHANGED

Added attention_config.py, attention_types.py, attention.py, attention_overlay.py, test_attention.py, attention_benchmark.py, attention_review.py, example config, nine attention docs, research register and integration audit. Additive pipeline/config/contracts/metrics/schema11/visualization wiring; benchmark injection; task-runner checks; README/replacement docs. No new dependency, audio subsystem, detector, risk geometry or Task017 implementation.

## C. ATTENTION ARCHITECTURE

Contract-only deterministic bounded engine. Single pipeline thread owns state. O(N log N) sorting/eviction, no pairwise geometry. At most 512 episodes, 512 suppressed candidates, one selected output and max_interruptions+4 scene ledger entries. No pending output queue. Input comparison policies share one contract.

## D. ATTENTIONDECISION CONTRACT

Frozen action, optional identity, priority, source risk and separate quality, trend, reasons, novelty, cooldown/repeat/escalation state, attention quality, event/episode, expiry, provenance and config hash. Set includes selected/suppressed decisions, scene status, reasons, risk provenance and upstream coverage. Category/direction null because current risk contract does not authorize them; no fabricated bearing/class.

## E. ATTENTION EPISODE MODEL

Session+entity+start-time identity; bounded last-seen/last-intent/level/high-water/repeat/continuity/event state. Disappearance/unknown closes active relevance; short return retains suppression history; >=5s gap permits new episode. Session resets and explicit seek reset isolate history. No ID merging.

## F. SILENT SEMANTICS

Explicit SILENT output even for empty scene. NO_INTERRUPT_NOT_A_SAFETY_VERDICT is semantic diagnostic, not all-clear. Every suppressed entity carries a reason; no absence-as-safe inference.

## G. NOVELTY

NEW, KNOWN, REAPPEARED, CHANGED, ESCALATED and DEESCALATED. Event identities stable through silence; action/level/repeat generation distinguish meaningful new intents. Reason-family CHANGED is diagnostic, not a new interrupt by itself. A final metadata-only CHANGED distinction followed the packet run; action-selection rules were unchanged and are covered by the final tests, short replay and corrected long run.

## H. FIRST ANNOUNCEMENT

Eligible new ELEVATED+ balanced or HIGH+ conservative evidence can ANNOUNCE immediately, subject to top-one/busy/scene protection. No initial debounce or multi-frame persistence filter, given already-low upstream coverage.

## I. REPEAT SUPPRESSION

Unchanged high evidence does not emit every frame. Novelty policy requires sustained HIGH/SEVERE and both cooldown and 30s continuous eligibility for a reminder. Unknown/quality gap restarts continuity. ELEVATED has no periodic reminder.

## J. COOLDOWN

Authoritative nanoseconds only: default 5s same-entity, 2s ordinary scene gap, 30s reminder. No wall-clock calls inside policy. Realtime pipeline maps processing lateness via replay anchor into now_ns; offline uses observation time.

## K. ESCALATION

Above the episode highest announced level -> ESCALATE. May bypass ordinary cooldown; scene/audio override requires strictly greater priority than recent maximum/current audio. High-water mark prevents ELEVATED/HIGH oscillation repeatedly escalating. Synthetic SEVERE tests exercise contract; Task015 never emits SEVERE.

## L. EVENT EXPIRY

Deadline=min(risk-set expiry, entity expiry, configured500ms lifetime from source state). Busy/out-ranked candidates are reconsidered only from fresh risk; no delayed backlog. Expired input yields EVENT_EXPIRED. Duplicate state yields silence; backwards clock raises before ledger mutation.

## M. UNDETERMINED HANDLING

UNDETERMINED_RISK remains explicit diagnostic silence, never LOW/safe. Empty evidence does not fabricate confidence, hazard absence or all-clear.

## N. EVIDENCE-QUALITY GATING

INSUFFICIENT always suppressed. DEGRADED admitted only under explicit research allow_degraded=true; can be disabled. Current attention quality remains DEGRADED even when a synthetic source says GOOD. No probability or human-validation claim.

## O. MULTIPLE-ENTITY RANKING

Descending ordinal risk, escalation first, first announcement before repeat, ascending stable entity ID. All source timestamps must match the set. Equal input permutations produce equal output. At most one new primary interruption.

## P. GLOBAL RATE LIMIT

Default 6 ordinary interruptions per rolling 60s and2s scene interval. Strict upward priority overrides are explicitly recorded and bounded by ordinal levels. ID churn cannot produce unbounded overrides. NAIVE intentionally disables ordinary timing protections for evaluation only.

## Q. AUDIO-BUSY / PREEMPTION CONTRACT

Abstract busy/active_priority consumed; lower/equal priority suppresses with AUDIO_BUSY. Strictly stronger intent may PREEMPT_AUDIO_INTENT. No playback, acknowledgement or queue implemented. Task017 must recheck expiry immediately before actual delivery.

## R. NAIVE POLICY RESULTS

Actions {'updates': 900, 'silent_updates': 24, 'suppressed': 32232, 'candidate_updates': 33108, 'ANNOUNCE': 783, 'selected_with_current_occupancy': 876, 'REPEAT': 93}; conditional risk-episode coverage 783/1507 (51.96%); silent-update ratio 2.67%. This is not reviewed hazard or usefulness performance.

## S. COOLDOWN POLICY RESULTS

Actions {'updates': 900, 'silent_updates': 840, 'suppressed': 33048, 'candidate_updates': 33108, 'ANNOUNCE': 60, 'selected_with_current_occupancy': 60}; conditional risk-episode coverage 60/1507 (3.98%); silent-update ratio 93.33%. This is not reviewed hazard or usefulness performance.

## T. NOVELTY + ESCALATION POLICY RESULTS

Actions {'updates': 900, 'silent_updates': 840, 'suppressed': 33048, 'candidate_updates': 33108, 'ANNOUNCE': 60, 'selected_with_current_occupancy': 60}; conditional risk-episode coverage 60/1507 (3.98%); silent-update ratio 93.33%. This is not reviewed hazard or usefulness performance.

## U. POLICY SELECTION

NOVELTY_ESCALATION / BALANCED_ATTENTION selected for Task017 research integration. Synthetic persistence/chatter shows lower repeat burden than cooldown; real coverage/burden tradeoffs remain explicit. No usefulness claim or threshold tuning against independent truth. Conservative mode available but no production-safe interpretation.

## V. TASK015 30-WINDOW RESULTS

All 30 original six-second windows evaluated at 5 Hz. 900 evaluated updates; 180.0s sampled exposure spread across600s. Source hash matched. No continuous-frame claim; gaps preserve source time and may reset identity/episodes. Local windows.jsonl retains full decisions/reasons; compact read-only review packet and public aggregate manifest prepared.

## W. HUMAN REVIEW STATUS

PENDING. All 30 review_label=null and DRAFT_REVIEW_REQUIRED. Existing Task015 review not overwritten. Labels available: SHOULD_INTERRUPT_NOW, SHOULD_REMAIN_SILENT, AMBIGUOUS, INSUFFICIENT_CONTEXT, TOO_EARLY, TOO_LATE, REPEAT_UNNECESSARY. Downloads remain HUMAN_LABELED_UNADJUDICATED. No server left running.

## X. CONDITIONAL ATTENTION COVERAGE

Primary covered 60/1507 eligible risk episodes (3.98%). Eligibility already requires upstream risk; this is conditional policy coverage, not source-event or hazard recall. Competing/unannounced episodes remain in denominator.

## Y. END-TO-END COVERAGE FUNNEL

Current short replay funnel: {'source_reviewed_events': None, 'events_missed_by_detector_tracker': None, 'reference': 'OBSERVED_SAME_ID_TRACKER_WINDOWS; SELECTION_BIASED', 'proxy_relevant': 52, 'interaction_predicted': 3, 'risk_raised': 12, 'risk_raised_given_interaction': 0}. Attention frozen-start per-policy funnels: {'NAIVE': {'events': {'FN': 50, 'TN': 49, 'TP': 2}, 'funnel': {'eligible_proxy_windows': 101, 'proxy_relevant': 52, 'attention_at_frozen_start': 2, 'attention_and_relevant': 2, 'interaction_and_risk_and_attention': 0}, 'first_attention_lead_proxy': {'count': 0, 'min_ns': None, 'max_ns': None, 'mean_ns': None, 'percentile_scope': 'recent_window', 'window_count': 0, 'p50_ns': None, 'p90_ns': None, 'p95_ns': None, 'p99_ns': None}, 'late_attention_delay_proxy': {'count': 3, 'min_ns': 793929650, 'max_ns': 1353826989, 'mean_ns': 1147901182.6666667, 'percentile_scope': 'recent_window', 'window_count': 3, 'p50_ns': 1295946909, 'p90_ns': 1353826989, 'p95_ns': 1353826989, 'p99_ns': 1353826989}}, 'COOLDOWN': {'events': {'FN': 52, 'TN': 49}, 'funnel': {'eligible_proxy_windows': 101, 'proxy_relevant': 52, 'attention_at_frozen_start': 0, 'attention_and_relevant': 0, 'interaction_and_risk_and_attention': 0}, 'first_attention_lead_proxy': {'count': 0, 'min_ns': None, 'max_ns': None, 'mean_ns': None, 'percentile_scope': 'recent_window', 'window_count': 0, 'p50_ns': None, 'p90_ns': None, 'p95_ns': None, 'p99_ns': None}, 'late_attention_delay_proxy': {'count': 0, 'min_ns': None, 'max_ns': None, 'mean_ns': None, 'percentile_scope': 'recent_window', 'window_count': 0, 'p50_ns': None, 'p90_ns': None, 'p95_ns': None, 'p99_ns': None}}, 'NOVELTY_ESCALATION': {'events': {'FN': 52, 'TN': 49}, 'funnel': {'eligible_proxy_windows': 101, 'proxy_relevant': 52, 'attention_at_frozen_start': 0, 'attention_and_relevant': 0, 'interaction_and_risk_and_attention': 0}, 'first_attention_lead_proxy': {'count': 0, 'min_ns': None, 'max_ns': None, 'mean_ns': None, 'percentile_scope': 'recent_window', 'window_count': 0, 'p50_ns': None, 'p90_ns': None, 'p95_ns': None, 'p99_ns': None}, 'late_attention_delay_proxy': {'count': 0, 'min_ns': None, 'max_ns': None, 'mean_ns': None, 'percentile_scope': 'recent_window', 'window_count': 0, 'p50_ns': None, 'p90_ns': None, 'p95_ns': None, 'p99_ns': None}}}. Source reviewed-event count and detector/tracker-missed events remain unknown. Future tracker proxy is selected on stable identity and censors gaps. Conditional attention cannot recover missing upstream risk.

## Z. TASK014 5.8% LIMITATION

Historical Task014 tracker-proxy recall 5.8% remains visible in contracts, overlays and docs. Independent current occupancy can raise risk without improving future-interaction recall. No end-to-end hazard ceiling/accuracy number is invented from an incomplete source denominator.

## AA. ANNOUNCEMENTS PER MINUTE

Packet source-span rates: {'NAIVE': 78.32610870290097, 'COOLDOWN': 6.002000666888963, 'NOVELTY_ESCALATION': 6.002000666888963}. Sampled-exposure rates: {'NAIVE': 261.0, 'COOLDOWN': 20.0, 'NOVELTY_ESCALATION': 20.0}. Denominators differ; neither is a wearer study.

## AB. REPEATS PER MINUTE

Source-span: {'NAIVE': 9.303101033677894, 'COOLDOWN': 0.0, 'NOVELTY_ESCALATION': 0.0}. Exposure-adjusted counts are in JSON. Reminders are intents, not proof audio played.

## AC. ESCALATIONS PER MINUTE

Source-span: {'NAIVE': 0.0, 'COOLDOWN': 0.0, 'NOVELTY_ESCALATION': 0.0}. Synthetic upward-level tests pass; absent real escalation observations do not validate the behavior in the field.

## AD. SUPPRESSION RATE

Per-policy suppressed candidate ratios: {'NAIVE': 0.9735411380935122, 'COOLDOWN': 0.9981877491844872, 'NOVELTY_ESCALATION': 0.9981877491844872}. Reason counters retained in JSON; unknown/expired, repeats, competition and scene protection are not conflated.

## AE. SILENT-PERIOD RATIO

Packet ratios: {'NAIVE': 0.02666666666666667, 'COOLDOWN': 0.9333333333333333, 'NOVELTY_ESCALATION': 0.9333333333333333}. Corrected realtime primary: 1.0. Silence is not utility or safety; expired CPU-pipeline evidence may force silence.

## AF. FIRST-ATTENTION LEAD PROXY

Frozen tracker-window proxy lead and late-delay counts: {'NAIVE': {'first_attention_lead_proxy': {'count': 0, 'min_ns': None, 'max_ns': None, 'mean_ns': None, 'percentile_scope': 'recent_window', 'window_count': 0, 'p50_ns': None, 'p90_ns': None, 'p95_ns': None, 'p99_ns': None}, 'late_attention_delay_proxy': {'count': 3, 'min_ns': 793929650, 'max_ns': 1353826989, 'mean_ns': 1147901182.6666667, 'percentile_scope': 'recent_window', 'window_count': 3, 'p50_ns': 1295946909, 'p90_ns': 1353826989, 'p95_ns': 1353826989, 'p99_ns': 1353826989}}, 'COOLDOWN': {'first_attention_lead_proxy': {'count': 0, 'min_ns': None, 'max_ns': None, 'mean_ns': None, 'percentile_scope': 'recent_window', 'window_count': 0, 'p50_ns': None, 'p90_ns': None, 'p95_ns': None, 'p99_ns': None}, 'late_attention_delay_proxy': {'count': 0, 'min_ns': None, 'max_ns': None, 'mean_ns': None, 'percentile_scope': 'recent_window', 'window_count': 0, 'p50_ns': None, 'p90_ns': None, 'p95_ns': None, 'p99_ns': None}}, 'NOVELTY_ESCALATION': {'first_attention_lead_proxy': {'count': 0, 'min_ns': None, 'max_ns': None, 'mean_ns': None, 'percentile_scope': 'recent_window', 'window_count': 0, 'p50_ns': None, 'p90_ns': None, 'p95_ns': None, 'p99_ns': None}, 'late_attention_delay_proxy': {'count': 0, 'min_ns': None, 'max_ns': None, 'mean_ns': None, 'percentile_scope': 'recent_window', 'window_count': 0, 'p50_ns': None, 'p90_ns': None, 'p95_ns': None, 'p99_ns': None}}}. Empty samples remain unavailable. Not physical collision-warning lead time.

## AG. CROWD RESULTS

NAIVE: {'updates': 600, 'silent_updates': 0, 'suppressed': 29400, 'candidate_updates': 30000, 'ANNOUNCE': 50, 'selected_with_current_occupancy': 0, 'REPEAT': 550}; COOLDOWN: {'updates': 600, 'silent_updates': 594, 'suppressed': 29994, 'candidate_updates': 30000, 'ANNOUNCE': 6, 'selected_with_current_occupancy': 0}; NOVELTY_ESCALATION: {'updates': 600, 'silent_updates': 594, 'suppressed': 29994, 'candidate_updates': 30000, 'ANNOUNCE': 6, 'selected_with_current_occupancy': 0} Global budget reduces entity-episode coverage; no crowd usefulness or group semantics validated.

## AH. MULTIPLE-ENTITY RESULTS

Permutation invariance, HIGH/ELEVATED ordering, top-one and priority reversal/preemption tested. No pairwise clustering, spatial duplicate merge or new identity reconciliation.

## AI. RISK-OSCILLATION RESULTS

NAIVE: {'updates': 600, 'silent_updates': 0, 'suppressed': 0, 'candidate_updates': 600, 'ANNOUNCE': 1, 'selected_with_current_occupancy': 0, 'ESCALATE': 1, 'REPEAT': 598}; COOLDOWN: {'updates': 600, 'silent_updates': 594, 'suppressed': 594, 'candidate_updates': 600, 'ANNOUNCE': 1, 'selected_with_current_occupancy': 0, 'ESCALATE': 1, 'REPEAT': 4}; NOVELTY_ESCALATION: {'updates': 600, 'silent_updates': 597, 'suppressed': 597, 'candidate_updates': 600, 'ANNOUNCE': 1, 'selected_with_current_occupancy': 0, 'ESCALATE': 1, 'REPEAT': 1} High-water escalation suppresses chatter without smoothing RiskAssessment or delaying first intent.

## AJ. ATTENTION LATENCY P50/P90/P95/P99

Packet compute 0.659/1.531/1.866/2.490 ms; corrected long compute 0.255/0.410/0.448/0.816 ms. Instrumented phase attribution: {'mean_ns_per_50_entity_update': {'validation': 2510810.0, 'history': 1337180.0, 'candidates': 11593120.0, 'quality_gates': 970776.6666666666, 'decision_construction': 1804570.0, 'ranking': 23440.0, 'selection': 4897460.0, 'output': 274320.0}, 'scope': 'Instrumented phase attribution includes tracing overhead; not runtime latency'}. Profiler includes overhead and is separate from runtime percentiles; JSON includes recording/serialization timings.

## AK. MANY-ENTITY STRESS

1/10/50/100/128/512 entities, 200 updates each; bounded state assertions passed. Two-hour equivalent sequence: {'hours': 2, 'updates': 72000, 'actions': {'ANNOUNCE': 720, 'SILENT': 71280}, 'final_history': 21, 'deterministic_two_runs': True}. Two independent engines agreed at every update; finite synthetic evidence is not a general leak proof. At 512 entities P95 exceeds the low-millisecond target; this remains a large-scene performance limitation despite passing the integrated throughput gate.

## AL. TEN-MINUTE REPLAY

Corrected final run: source 600.000s; wall 605.094s; counts {'source': 18001, 'decoded': 18001, 'accepted': 18000, 'processed': 63, 'dropped': 17938, 'failed': 0}; attention updates 63; actions {'updates': 63, 'silent_updates': 63, 'suppressed': 1305, 'candidate_updates': 1305}; peak episode ledger 0. Whole-process memory in JSON. Preliminary pre-expiry-fix run retained, not used for completion.

## AM. FULL-PIPELINE UPDATE RATE

Final processed/source-span = 0.105 updates/s. Full CPU perception remains below wearable realtime requirements. This is not corrected by a cheap attention policy.

## AN. THROUGHPUT OVERHEAD

Same-process3s ABBA disabled/enabled/enabled/disabled: [25.469, 25.09, 25.038, 24.73] seconds; aggregate change -0.139%, provisional <=5% engineering gate passed. Causal proxy scoring disabled in both sides; no comparison timelines/other policies in timed primary. No speedup, statistical certainty or target-hardware guarantee claimed.

## AO. ATTENTION POLICY SWAP TEST

Naive, cooldown and novelty implementations return the same immutable contract. Injected replacement pipeline/recording/reset test passes; no consumer imports a policy implementation.

## AP. RISK ENGINE SWAP TEST

Alternate risk producer/provenance and injected slow risk producer feed attention unchanged. Task015 deliberately rejected a weighted runtime; no fabricated rule-vs-weighted execution/accuracy result. Any future weighted engine must honor the same freshness/quality/identity contract.

## AQ. COMPONENT REPLACEMENT AUDIT

Attention imports only Sentinel contract/config types. Detector/tracker/depth/flow/ego/segmenter/world/corridor/trajectory implementations remain upstream. Real replay and synthetic contract swaps verify software compatibility, not every vendor/target combination.

## AR. TASK001-016 INTEGRATION AUDIT

See docs/architecture/TASK001_016_INTEGRATION_AUDIT.md for every retained boundary. 004->016 PASS;007/011->016 PARTIAL (physical identity);014->016 PARTIAL (coverage/physical limits);015->016 PASS;016->recording PASS;016->future017 PASS contract only. Earlier physical-evidence PARTIAL statuses remain; no hidden promotion.

## AS. FUTURE TASK017 CONTRACT

Consume AttentionDecisionSet only; render deterministic AlertIntent/AlertPresentation from entity when present, source risk/quality, semantic reasons, priority and repeat/escalation type. Category/direction may be null and must not be guessed. Actual playback/haptics, acknowledgement and expiry-at-delivery are planned. Task017 not started.

## AT. R&D EXPERIMENTS

20 RND-ATT entries include QUESTION, WHY IT MATTERS, HYPOTHESIS, EXPERIMENT, METRICS, DECISION CRITERION, STATUS. Synthetic, packet, proxy, latency/load evidence linked here. Personalization/human usefulness remain planned; no neural/RL policy or automatic feedback learning.

## AU. PRIVACY / SECURITY

No new dependency, telemetry, upload, biometric identification, external API or secret. Private footage/paths/full per-entity timelines remain ignored locally. Public artifacts contain aggregate metrics/source hash only. Review reuses loopback allowlisted GET/range server with no writes or directory browse. Executed npm security gate reported no npm advisories. No new dependencies were added. A separate current Python/JVM vulnerability database scan was not performed; this is not a zero-vulnerability guarantee.

## AV. ADVERSARIAL AUDIT

CRITICAL: no outstanding implementation finding after checks. HIGH fixed: realtime processing age omitted before expiry; corrected and regression-tested with simulated clocks and repeated long run. Also corrected persistence reset, distinct event identities, bounded eviction, signed proxy lead handling and reset-failure cleanup so replacement components cannot skip recorder/worker shutdown. MEDIUM: unvalidated quality/thresholds/human preferences, coverage lost to load protection, upstream5.8% recall/identity/physical uncertainty and slow perception. LOW: bounded overlay density; nullable direction/category limits future wording. Review was read-only before targeted fixes. No human validation fabricated.

## AW. TEST COUNTS

824 total =193 Guardian +604 perception-lab +24 web +3 API. 46 Task016 tests added. These are software checks, not hazard or usefulness qualification.

## AX. FULL VERIFICATION

npm.cmd run verify exit0: formatting, Ruff, strict mypy, ESLint, TypeScript, Spotless, SpotBugs, tests, production builds, dependency/security review and runtime smoke. git diff --check separately passed. Full log: benchmark-results/task016/verify.log. Hosted CI, production deployment, target devices, separate Python/JVM vulnerability database scans and human validation not executed.

## AY. PRIMARY_ATTENTION_POLICY_FOR_TASK017

NOVELTY_ESCALATION with BALANCED_ATTENTION, default research config. No production-safe parameter claim. Rationale: explicit first intent, stronger escalation, sustained reminders and bounded crowd burden with visible coverage losses.

## AZ. REMAINING RISKS

Insufficient upstream coverage, imperfect tracking identity, unvalidated physical depth/motion/TTC, mostly unknown risk, slow/variable CPU pipeline, sparse review context, no independent source-event denominator, pending human interruption preference/usefulness. All 63 updates in the corrected realtime replay were silent:1305 candidates expired during upstream processing. This is a measured live-use limitation, not evidence that the scene was safe. Offline results cannot establish realtime usefulness. Future cloud/mobile runtime and real audio delivery unverified.

## BA. FINAL VERDICT

TASK016 COMPLETE: YES — local prototype/research engineering.

ENGINEERING QUALIFIED FOR TASK017: YES — contract/software scope, explicit evidence limits.

ATTENTION_POLICY_VALIDATED_WITH_HUMANS: NO.

END_TO_END_HAZARD_RECALL_VALIDATED: NO.

ALERT_USEFULNESS_VALIDATED: NO.

PRODUCTION_SAFETY_VALIDATED: NO.

Task017 NOT STARTED.

### Many-entity latency

| Entities | P50 ms | P95 ms | P99 ms |
| -------- | -----: | -----: | -----: |
| 1        |  0.034 |  0.053 |  0.126 |
| 10       |  0.219 |  0.345 |  0.371 |
| 50       |  1.078 |  1.911 |  2.268 |
| 100      |  4.211 |  6.066 |  6.679 |
| 128      |  6.052 |  7.778 |  9.538 |
| 512      | 25.432 | 34.488 | 58.044 |
