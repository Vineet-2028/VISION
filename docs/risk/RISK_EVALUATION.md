# Risk evaluation and draft review

IMPLEMENTED: deterministic scenario and ordering tests, static obstacle regression, unknown/stale/predicted gates, diagnostic-only TTC/CPA, identity expiry, immutable outputs, engine replacement, recording and overlay tests. Real replay measures distribution, latency and a bounded tracker-proxy funnel. It never calls those results hazard accuracy.

The development evaluation freezes each risk decision at prediction time, then uses the same future tracker reference and censoring rules as Task014 (250 ms maximum observation gap, final observation within 100 ms of horizon). There is no feedback to live predictions. Sensitivity uses three preselected entry thresholds, without optimizing them on final evidence.

Runtime qualification records independent-process comparisons and a same-process disabled/enabled/enabled/disabled control when process-to-process variation prevents attribution. The provisional engineering gate for that control is at most 5% aggregate added wall time, alongside isolated risk-stage timing. This short control is not a statistical or target-device performance guarantee; unfavorable independent-process measurements remain in the report.

The local packet contains 30 six-second windows spread over the first ten minutes of SENTINEL_FIRST_PERSON_V1. Temporal coverage is chosen independently of detector confidence; scenario tags begin empty. Pedestrian/bicycle/vehicle/crowd/turn/low-light diversity requires review and cannot be inferred from temporal sampling alone. Low-light examples may be absent in this footage.

All windows start DRAFT_REVIEW_REQUIRED. Labels are CLEARLY_RELEVANT_INTERACTION, CLEARLY_IRRELEVANT, AMBIGUOUS or INSUFFICIENT_VISUAL_EVIDENCE, with notes. Downloaded human labels remain HUMAN_LABELED_UNADJUDICATED, not automatically validated ground truth. No human review is fabricated. RISK_GROUND_TRUTH_VALIDATED remains NO until independent review/adjudication supports a claim.
