# Alert timing

MEASURED results live in the Task017 research report, with private raw outputs under benchmark-results/task017. Distribution stores lifetime count/min/max/mean and nearest-rank P50/P90/P95/P99 over a bounded 2048-sample recent window. Benchmark total includes instrumentation; core timing excludes timeline serialization. Report milliseconds from nanoseconds explicitly.

Source-to-alert age is now minus original source observation, when available. Attention-to-alert age uses decision generation time; they are not interchangeable. RISK_STATE_ONLY identifies incomplete source-age provenance. Historical Task016 frozen records lack original source timestamps and must not fabricate zero source age. Realtime pipeline result-age distributions remain available even if no alert is eligible.

ON_TIME_CANDIDATE <=200ms, LATE_CANDIDATE >200ms, EXPIRED at deadline; unknown source age is AGE_UNAVAILABLE. These are configurable prototype diagnostics, not human reaction-time validation. Speech duration is word count times 60/words_per_minute, without TTS dependency.

Do not report low alert-stage compute latency as low end-to-end delay. All Task016 realtime candidates expired before Task017 existed; Task017 preserves this gate.
