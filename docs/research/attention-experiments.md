# Attention research register

Research settings only. Exact executed measurements are linked from the Task016 report.

## RND-ATT-001: naive risk-to-alert burden

QUESTION: What is the effect of naive risk-to-alert burden?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: Per-update risk forwarding produces repeated intent floods.

EXPERIMENT: Replay identical risk sets through all three policies.

METRICS: Intents/minute; episode coverage.

DECISION CRITERION: Reject naive as primary if unchanged scenarios emit every update.

STATUS: IMPLEMENTED; see Task016 report for executed evidence and limitations.

## RND-ATT-002: cooldown effectiveness

QUESTION: What is the effect of cooldown effectiveness?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: Time-based cooldown reduces repetition at variable source cadence.

EXPERIMENT: Compare cooldown versus naive at synthetic 10Hz and real observation cadence.

METRICS: Repeats/minute; cooldown suppression count.

DECISION CRITERION: Must not depend on frame count; retain first eligible episode when not competing.

STATUS: IMPLEMENTED; see Task016 report for executed evidence and limitations.

## RND-ATT-003: novelty suppression

QUESTION: What is the effect of novelty suppression?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: One episode needs fewer interrupts than one per frame.

EXPERIMENT: Run 100 unchanged updates and a 60s persistent HIGH sequence.

METRICS: Initial announcements; unique episodes; reminders.

DECISION CRITERION: One initial intent; bounded reminders, no per-frame announcement.

STATUS: IMPLEMENTED; see Task016 report for executed evidence and limitations.

## RND-ATT-004: escalation override

QUESTION: What is the effect of escalation override?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: A genuinely higher ordinal risk can interrupt during ordinary cooldown.

EXPERIMENT: ELEVATED->HIGH and HIGH->SEVERE fixtures with active scene/audio protection.

METRICS: ESCALATE count; override reason; highest emitted level.

DECISION CRITERION: Allow strict escalation; reject repeated oscillation overrides.

STATUS: IMPLEMENTED; see Task016 report for executed evidence and limitations.

## RND-ATT-005: repeat interval

QUESTION: What is the effect of repeat interval?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: A 30s sustained HIGH reminder reduces burden relative to 5s cooldown repeats.

EXPERIMENT: Persistent HIGH and a quality gap shortly before reminder eligibility.

METRICS: Repeat count; repeat timing; quality-gap reset.

DECISION CRITERION: Repeat requires continuous eligible risk, not elapsed cooldown alone.

STATUS: IMPLEMENTED; see Task016 report for executed evidence and limitations.

## RND-ATT-006: global rate limiting

QUESTION: What is the effect of global rate limiting?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: A rolling scene budget bounds load even with ID churn.

EXPERIMENT: Create many novel IDs within one minute with increasing/equal risk.

METRICS: Maximum burst; intents/window; override count.

DECISION CRITERION: At most configured ordinary budget plus bounded strict priority increases.

STATUS: IMPLEMENTED; see Task016 report for executed evidence and limitations.

## RND-ATT-007: multiple-entity ranking

QUESTION: What is the effect of multiple-entity ranking?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: Stronger/newer evidence should win deterministic competition.

EXPERIMENT: Shuffle equal-priority input order; mix HIGH/ELEVATED and new/repeat candidates.

METRICS: Selected identity; suppressed reasons.

DECISION CRITERION: Identical selected ID across permutations; stronger ordinal priority first.

STATUS: IMPLEMENTED; see Task016 report for executed evidence and limitations.

## RND-ATT-008: crowd alert flooding

QUESTION: What is the effect of crowd alert flooding?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: Top-one plus global budget prevents per-person flood.

EXPERIMENT: 50 simultaneous ELEVATED entities over 600 updates.

METRICS: Intents/minute; entity-episode coverage lost.

DECISION CRITERION: Report suppression cost explicitly; no per-entity-per-update emission.

STATUS: IMPLEMENTED; see Task016 report for executed evidence and limitations.

## RND-ATT-009: UNDETERMINED handling

QUESTION: What is the effect of UNDETERMINED handling?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: Unknown risk should be diagnostic silence without a safety claim.

EXPERIMENT: All-unknown and empty risk sets.

METRICS: Decision/reason; scene output.

DECISION CRITERION: Explicit UNDETERMINED_RISK or no-evidence silence; never safe/all-clear.

STATUS: IMPLEMENTED; see Task016 report for executed evidence and limitations.

## RND-ATT-010: low-quality HIGH risk handling

QUESTION: What is the effect of low-quality HIGH risk handling?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: Quality collapse must not strengthen interruption.

EXPERIMENT: INSUFFICIENT HIGH and DEGRADED HIGH with allow_degraded on/off.

METRICS: Quality-gate count; selected intents.

DECISION CRITERION: Always reject insufficient; degraded admission must be explicit research policy.

STATUS: IMPLEMENTED; see Task016 report for executed evidence and limitations.

## RND-ATT-011: risk oscillation/chatter

QUESTION: What is the effect of risk oscillation/chatter?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: An episode high-water mark prevents repeated escalation chatter.

EXPERIMENT: Alternate ELEVATED/HIGH for 600 updates.

METRICS: Escalations, repeats and silent ratio.

DECISION CRITERION: At most one rise to previously unannounced HIGH in an episode.

STATUS: IMPLEMENTED; see Task016 report for executed evidence and limitations.

## RND-ATT-012: hysteresis/debounce tradeoff

QUESTION: What is the effect of hysteresis/debounce tradeoff?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: Initial debounce risks losing already-scarce upstream events.

EXPERIMENT: Compare immediate first intent with high-water-only escalation suppression.

METRICS: First-intent delay; oscillation escalation count.

DECISION CRITERION: Keep zero initial debounce; do not add a persistence filter without measured justification.

STATUS: IMPLEMENTED; see Task016 report for executed evidence and limitations.

## RND-ATT-013: Task014 low-recall interaction

QUESTION: What is the effect of Task014 low-recall interaction?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: Attention cannot recover missing predicted interactions.

EXPERIMENT: Preserve causal Task014 tracker proxy and risk/attention funnel.

METRICS: Historical5.8%; current proxy counts; unknown source denominator.

DECISION CRITERION: Never report conditional coverage as hazard recall.

STATUS: IMPLEMENTED; see Task016 report for executed evidence and limitations.

## RND-ATT-014: attention event coverage

QUESTION: What is the effect of attention event coverage?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: Burden control loses some risk-eligible episodes.

EXPERIMENT: Compare emitted distinct episode IDs with eligible episode IDs on the same stream.

METRICS: Conditional episode coverage for each policy.

DECISION CRITERION: Publish lost coverage; no blanket accuracy claim from selected events.

STATUS: IMPLEMENTED; see Task016 report for executed evidence and limitations.

## RND-ATT-015: alerts/minute

QUESTION: What is the effect of alerts/minute?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: Scene-span and sampled-exposure rates can differ substantially.

EXPERIMENT: Compute source-span rates and exposure rates for all 30 windows.

METRICS: ANNOUNCE/REPEAT/ESCALATE per minute.

DECISION CRITERION: Label denominators; no extrapolation to continuous wearable use.

STATUS: IMPLEMENTED; see Task016 report for executed evidence and limitations.

## RND-ATT-016: repeat burden

QUESTION: What is the effect of repeat burden?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: Novelty policy should reduce unnecessary repeats beyond cooldown alone.

EXPERIMENT: Persistent and oscillating risk with three policies.

METRICS: Repeat counts and ratio versus naive.

DECISION CRITERION: Choose simpler selective policy if coverage is comparable; do not optimize silence alone.

STATUS: IMPLEMENTED; see Task016 report for executed evidence and limitations.

## RND-ATT-017: silent-period ratio

QUESTION: What is the effect of silent-period ratio?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: Explicit silence is observable useful output, but 100% silence may reveal missing/expired evidence.

EXPERIMENT: Measure synthetic, packet and realtime streams separately.

METRICS: Silent updates/total; suppression reasons.

DECISION CRITERION: Explain silence causes; no safety or utility inference.

STATUS: IMPLEMENTED; see Task016 report for executed evidence and limitations.

## RND-ATT-018: attention latency

QUESTION: What is the effect of attention latency?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: Contract-only policy should add little cost relative to perception.

EXPERIMENT: Isolated stress, instrumented phases and integrated stage timing.

METRICS: P50/P90/P95/P99; history/ranking/construction/recording attribution.

DECISION CRITERION: Report outliers and profiler overhead; no device guarantee.

STATUS: IMPLEMENTED; see Task016 report for executed evidence and limitations.

## RND-ATT-019: many-entity scaling

QUESTION: What is the effect of many-entity scaling?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: Bounded O(N log N) selection should avoid quadratic competition and leaks.

EXPERIMENT: 1/10/50/100/128/512 stress plus deterministic two-hour synthetic run.

METRICS: Compute distribution; peak ledger size; determinism.

DECISION CRITERION: State bounds never exceeded; no duplicate or stale queue growth.

STATUS: IMPLEMENTED; see Task016 report for executed evidence and limitations.

## RND-ATT-020: future personalization need

QUESTION: What is the effect of future personalization need?

WHY IT MATTERS: Interruption burden must be balanced against lost relevant-event coverage, with upstream uncertainty visible.

HYPOTHESIS: Useful frequency depends on users and environments.

EXPERIMENT: Future consented review of sensitivity, mobility, hearing and familiarity preferences.

METRICS: USEFUL_ALERT/UNHELPFUL_ALERT/TOO_LATE/TOO_FREQUENT/MISSED_EVENT.

DECISION CRITERION: Do not implement adaptive learning before representative human evidence.

STATUS: PLANNED; human study required.
