# Alert experiments

Research proposals and measured software experiments; no human results fabricated.

## RND-ALERT-001: category + direction comprehensibility

QUESTION: Can listeners identify the object and bearing from a short phrase?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: A short noun plus authorized direction is sufficient in simple scenes.

EXPERIMENT: Present randomized authorized phrases with consented blind/low-vision reviewers; retain unknown cases.

METRICS: Correct interpretation, response time, requests for repetition.

DECISION CRITERION: Pre-register participant inclusion and comprehension target before recruiting.

STATUS: PLANNED human/product evaluation; no validated outcome claimed.

## RND-ALERT-002: crossing phrase design

QUESTION: Does crossing from left distinguish origin from destination?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: Explicit from is less ambiguous than a bare directional word.

EXPERIMENT: Compare crossing from left/right against crossing ahead using reviewed motion clips.

METRICS: Origin/destination confusion and comprehension.

DECISION CRITERION: Choose only after independent interpretation and user preference agree.

STATUS: PLANNED human/product evaluation; no validated outcome claimed.

## RND-ALERT-003: approaching phrase design

QUESTION: Is approaching left understood as object position or instruction?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: Noun-first environmental wording avoids navigation interpretation.

EXPERIMENT: Compare approaching variants with verified approach evidence and ask users to paraphrase.

METRICS: Navigation misinterpretation, clarity.

DECISION CRITERION: Reject variants interpreted as an instruction to move.

STATUS: PLANNED human/product evaluation; no validated outcome claimed.

## RND-ALERT-004: static-obstacle wording

QUESTION: Is a stationary object warning useful without TTC?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: Category plus authorized direction can be useful without numeric timing.

EXPERIMENT: Use independently reviewed stationary obstacles and compare category-specific versus generic nouns.

METRICS: Clarity, usefulness, false motion inference.

DECISION CRITERION: Do not authorize static wording from occupancy alone.

STATUS: PLANNED human/product evaluation; no validated outcome claimed.

## RND-ALERT-005: unknown-category fallback

QUESTION: Is Object too vague to help?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: An honest generic fallback is preferable to an incorrect specific noun.

EXPERIMENT: Review unknown-class clips and compare Object, Obstacle and silence with users.

METRICS: Usefulness, false obstruction implication, silence preference.

DECISION CRITERION: Do not change the fallback solely to make demonstrations richer.

STATUS: PLANNED human/product evaluation; no validated outcome claimed.

## RND-ALERT-006: unknown-direction fallback

QUESTION: Is omission preferable to guessed ahead?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: Omitting unsupported direction avoids false orientation.

EXPERIMENT: Review unknown-bearing fixtures and user paraphrases.

METRICS: Invented bearing rate, comprehension.

DECISION CRITERION: Zero fabricated bearings; user preference remains a separate gate.

STATUS: PLANNED human/product evaluation; no validated outcome claimed.

## RND-ALERT-007: repeat wording

QUESTION: Does repeating the full phrase work after attention interruption?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: Full phrases are less ambiguous than Still ahead or It.

EXPERIMENT: Randomize interrupted-context playback of standalone and abbreviated phrases.

METRICS: Context dependence, comprehension, perceived burden.

DECISION CRITERION: Require adequate standalone comprehension before abbreviation.

STATUS: PLANNED human/product evaluation; no validated outcome claimed.

## RND-ALERT-008: escalation wording

QUESTION: Can emphasis indicate escalation without changing facts?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: Style-only escalation preserves evidence while indicating renewed importance.

EXPERIMENT: Compare metadata-guided future audio emphasis using identical semantic phrases.

METRICS: Urgency recognition, panic, false certainty.

DECISION CRITERION: Do not introduce stronger collision claims.

STATUS: PLANNED human/product evaluation; no validated outcome claimed.

## RND-ALERT-009: phrase length

QUESTION: How many words does the V1 matrix produce?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: All deterministic phrases fit the short-warning bounds.

EXPERIMENT: Execute the 360-case fixed expected-phrase matrix and count words/characters.

METRICS: Words, characters, rejected over-length phrases.

DECISION CRITERION: No phrase above configured 6-word/64-character defaults.

STATUS: MEASURED software evidence in Task017 report; human/physical validity remains UNVALIDATED.

## RND-ALERT-010: estimated speech duration

QUESTION: What duration does the configured word-rate heuristic predict?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: V1 phrases are brief at 180 words/minute.

EXPERIMENT: Compute duration across the matrix without a TTS engine.

METRICS: Estimated seconds, maximum phrase duration.

DECISION CRITERION: Flag >2 seconds; never call heuristic duration actual playback time.

STATUS: MEASURED software evidence in Task017 report; human/physical validity remains UNVALIDATED.

## RND-ALERT-011: expiry policy

QUESTION: Does each output boundary reject an expired alert?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: Independent checks at render, acceptance and consumption prevent stale delivery.

EXPERIMENT: Inject exact-deadline and post-render/queued delays.

METRICS: Expired acceptances and status reason.

DECISION CRITERION: Zero accepted expired text; hardware delivery still untested.

STATUS: MEASURED software evidence in Task017 report; human/physical validity remains UNVALIDATED.

## RND-ALERT-012: stale-alert suppression

QUESTION: Can a delayed pipeline emit a historical backlog?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: A one-slot presenter plus expiry prevents backlog playback.

EXPERIMENT: Exercise supersession, duplicate input, backward clocks and delayed consumption.

METRICS: Queue peak, stale acceptance, duplicate delivery.

DECISION CRITERION: One pending slot and zero stale/duplicate acceptance.

STATUS: MEASURED software evidence in Task017 report; human/physical validity remains UNVALIDATED.

## RND-ALERT-013: source-to-alert result age

QUESTION: Can small alert compute time hide old evidence?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: Separate source and attention ages expose upstream delay.

EXPERIMENT: Compare fresh offline replay, delayed realtime replay and missing-source records.

METRICS: Source age, decision age, compute latency, unavailable counts.

DECISION CRITERION: Never substitute attention age or zero for unknown source age.

STATUS: MEASURED software evidence in Task017 report; human/physical validity remains UNVALIDATED.

## RND-ALERT-014: realtime vs offline output

QUESTION: Are offline demonstrations distinguishable from live results?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: Explicit mode fields and labels prevent qualification confusion.

EXPERIMENT: Inspect pipeline recordings and 30-window review packet.

METRICS: Mode consistency, realtime/offline counts.

DECISION CRITERION: Every offline record and review is labeled; do not transfer performance claims.

STATUS: MEASURED software evidence in Task017 report; human/physical validity remains UNVALIDATED.

## RND-ALERT-015: Task016 3.98% coverage ceiling

QUESTION: Can wording recover attention-suppressed episodes?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: A downstream renderer cannot recover upstream nonselected events.

EXPERIMENT: Use the frozen 900 updates and 1507 eligible entity-episode denominator.

METRICS: Selected episodes versus rendered outputs, suppression reasons.

DECISION CRITERION: Retain 3.98% inherited limitation; no hazard-recall interpretation.

STATUS: PLANNED human/product evaluation; no validated outcome claimed.

## RND-ALERT-016: Task014 5.8% interaction ceiling

QUESTION: Can better language compensate for missed interaction forecasts?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: Language changes cannot recover missing forecasts.

EXPERIMENT: Join independently reviewed source events to the full upstream funnel in Task018.

METRICS: Interaction misses, source denominator, conditional coverage.

DECISION CRITERION: Retain historical 5.8% tracker-proxy recall until valid re-evaluation.

STATUS: PLANNED human/product evaluation; no validated outcome claimed.

## RND-ALERT-017: presentation latency

QUESTION: How much time does intent and rendering add?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: Deterministic construction has sub-millisecond typical latency.

EXPERIMENT: Measure intent, template, presentation, sink and total timing; pair full-pipeline enabled/disabled runs.

METRICS: P50/P90/P95/P99/max, ABBA wall overhead.

DECISION CRITERION: Report measured tails and source age; no target-device guarantee.

STATUS: MEASURED software evidence in Task017 report; human/physical validity remains UNVALIDATED.

## RND-ALERT-018: queue boundedness

QUESTION: Do presenter state and IDs grow with session duration?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: Fixed histories and monotonic watermark bound storage without duplicate delivery.

EXPERIMENT: Run 72000 updates (two observation-hours), compare two deterministic runs and replay old IDs.

METRICS: Pending count, history/ID count, duplicate acceptance.

DECISION CRITERION: At most one slot and configured history; reject evicted old decisions by timestamp.

STATUS: MEASURED software evidence in Task017 report; human/physical validity remains UNVALIDATED.

## RND-ALERT-019: future speech vs haptic mapping

QUESTION: Can a future haptic adapter consume the same semantic intent?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: Authorized direction and urgency suffice without parsing text.

EXPERIMENT: Design directional and unknown-direction mapping with users and device constraints.

METRICS: Mapping ambiguity, missed/false pattern interpretation.

DECISION CRITERION: No directional vibration from UNKNOWN; no implementation in Task017.

STATUS: PLANNED human/product evaluation; no validated outcome claimed.

## RND-ALERT-020: personalized alert language

QUESTION: Which preferences materially improve usefulness?

WHY IT MATTERS: Evidence-bound warnings must be useful without misleading the user.

HYPOTHESIS: Speech rate, vocabulary and modality may vary among users.

EXPERIMENT: Run consented participatory research before adding profiles or accounts.

METRICS: Preference stability, comprehension, burden, accessibility.

DECISION CRITERION: Add only preferences supported by repeatable user evidence.

STATUS: PLANNED human/product evaluation; no validated outcome claimed.
