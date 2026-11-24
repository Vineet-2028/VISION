# Evidence quality and freshness

IMPLEMENTED: risk and quality are separate. HIGH/DEGRADED is valid. UNDETERMINED/INSUFFICIENT means evidence cannot support classification. This prototype never emits GOOD evidence quality because upstream event coverage and sensing remain unvalidated.

World, corridor, trajectory and interaction schema/session/time/provenance must align. The engine checks observed versus predicted track status, current entity timestamp, observed age, source identity/age/status, corridor heading and relation sources, last trajectory observation and forecast quality. Defaults allow at most 500 ms source age. Unusable trajectory does not erase independently fresh current occupancy. Stale depth cannot support metric corridor evidence; missing depth does not disable independently valid image occupancy.

Reason codes retain upstream low recall, predicted-only tracks, explicit fragmentation indicators, unreliable trajectory, degraded corridor, unvalidated metric sensing/motion, unverified semantics and insufficient evidence. No arbitrary confidence average is used. An absent fragmentation reason is not evidence that identity is correct.

Trend is a comparison with a bounded, recent prior classification, never smoothing. Unknown, expired or new identity yields UNKNOWN trend. RISING/STABLE/FALLING do not trigger alerts.
