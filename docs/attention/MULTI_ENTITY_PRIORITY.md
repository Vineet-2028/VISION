# Competition and alert-load control

IMPLEMENTED comparator: descending ordinal risk priority; escalation before non-escalation; new announcement before repeat; ascending stable entity ID. Source timestamps must match the set, so they cannot serve as an artificial urgency tie-break. Input order does not determine ties.

Exactly one primary decision per update. Other qualifying candidates record PREEMPTED_BY_HIGHER_PRIORITY. Global defaults: at least 2s between ordinary interruptions, at most 6 ordinary interruptions per rolling 60s. Strictly increasing priority overrides are separately explained and bounded by the four risk ordinals. Recent ledger capacity is max_interruptions+4.

Crowds do not generate an interruption per person per update. Bounded global protection applies even with identity churn. No category-dependent crowd clustering or cross-ID reconciliation is implemented; later arrivals can still consume the scene budget. Human usefulness of this selection remains UNVALIDATED.

NAIVE is an explicit evaluation baseline: one qualifying intent each update without repeat/global suppression, retaining identity/quality/freshness/top-one gates. COOLDOWN adds repeat and global timing. NOVELTY_ESCALATION adds persistence reminders and high-water escalation. Only the measured primary policy is recommended for integration.
