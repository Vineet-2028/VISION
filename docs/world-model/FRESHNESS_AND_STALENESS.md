# Freshness, ordering and retention

IMPLEMENTED source clock is explicit and bound on first accepted event. UNKNOWN clocks, wrong sessions/sources, future observation times and time reversal are rejected. Snapshot time cannot precede accepted evidence. Backward seek requires explicit reset; no historical recomputation.

Each source has one bounded watermark. Same-source equal/older timestamp or non-increasing sequence is rejected/idempotent with a diagnostic. Different sources can arrive asynchronously within late_ns; there is no event backlog. Exact object associations still require the current observed track identity. No nearest or interpolation fallback is hidden. First accepted result wins for same-source/frame duplicates, including conflicting retries.

Every event passes an explicit current source-clock now. Default allowed lateness is 1 second, maximum configurable 5 seconds. Default ordinary freshness is 0.5 second, semantic/surface freshness 1 second. Defaults are research controls, not production safety thresholds. Source observation age remains separate from delivery and processing durations.

Status distinguishes FRESH, STALE, PREDICTED, PROPAGATED, DEGRADED, UNRELIABLE, UNAVAILABLE and FAILED. Original observation status/quality/validation are separate axes: propagated evidence can later be stale, and fresh evidence can remain unverified. Entity observation_age_ns is based on last actual observation, while tracking source age can be based on a newer prediction tick.

Expiry and payload retention are bounded independently. Default retention 5 seconds. Failure ticks retain their own status but do not refresh an old payload. History horizon/count, source watermarks (fixed source names), diagnostic deque, maximum regions and entity ceilings bound memory independent of recording duration.

PROVISIONAL sensitivity: increasing freshness keeps estimates current-labelled longer but cannot qualify their accuracy. Increasing lateness accepts more delayed semantic evidence; decreasing it sheds stale workload. Actual replay reports rejection/age consequences; do not tune thresholds solely to make a capability green.
