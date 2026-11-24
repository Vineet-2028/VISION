# Cooldown, quality and expiry

IMPLEMENTED: all policy time comes from authoritative nanosecond state timestamps. No system clock, sleeps, frame-count cooldown or background policy worker. Callers may supply now_ns to reject a delayed risk set; it cannot precede the risk timestamp or previously consumed now.

Meaningful escalation above the episode's highest emitted level bypasses normal entity cooldown. Global protection may be bypassed only above the strongest recent emitted/audio priority; the reason HIGHER_PRIORITY_OVERRIDE is recorded. This prevents every new high-risk ID from bypassing the scene budget. A busy channel is preemptible only by a strictly stronger qualifying intent; PREEMPT_AUDIO_INTENT is explicit. Actual playback remains Task017.

No stale backlog is stored. Audio-busy and outranked candidates are re-evaluated only on a new fresh risk set. Expired evidence produces EVENT_EXPIRED. UNDETERMINED produces UNDETERMINED_RISK. INSUFFICIENT always produces LOW_EVIDENCE_QUALITY. DEGRADED is explicitly allowed by default for research and may be disabled; GOOD is not fabricated.

Conservative mode requires HIGH; balanced mode admits ELEVATED. The names describe interruption behavior, not safety. Risk quality collapse cannot trigger stronger attention.
