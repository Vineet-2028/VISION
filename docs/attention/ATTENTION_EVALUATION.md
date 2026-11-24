# Evaluation protocol

IMPLEMENTED tools: attention_benchmark.py compares NAIVE, COOLDOWN and NOVELTY_ESCALATION on identical risk sets; attention_review.py extends Task015's 30 draft windows without altering their original annotations. All attention labels start null/DRAFT_REVIEW_REQUIRED.

Metrics distinguish update counts, distinct risk episodes, emitted episode coverage, announcement/repeat/escalation rates, suppressed-candidate ratio, silent-update ratio, interruption intervals, latency and bounded-history stress. Conditional episode coverage uses risk-eligible episode IDs, not independently annotated hazards. The naive baseline supplies the least-suppressed comparison, not ground truth.

A causal Task014 proxy callback retains frozen-start attention decisions before observing future tracker motion. Lead uses first attention within the same pending tracked window relative to its later proxy entry. Missing/censored identities remain explicit. No source-event denominator exists; detector/tracker misses and end-to-end hazard recall are unknown.

The packet samples all 30 six-second windows at 5Hz; gaps remain real observation-time gaps and can reset episodes. Rates over the 600s source span differ from rates over 180s sampled exposure. This is a sparse development replay, not complete-frame qualification. Scenario diversity and human labels are unreviewed.

MEASURED results and exact commands belong in the Task016 report; do not copy historical numbers as current results. Planned independent labels: SHOULD_INTERRUPT_NOW, SHOULD_REMAIN_SILENT, AMBIGUOUS, INSUFFICIENT_CONTEXT, TOO_EARLY, TOO_LATE, REPEAT_UNNECESSARY. Labels downloaded by a reviewer remain HUMAN_LABELED_UNADJUDICATED.
