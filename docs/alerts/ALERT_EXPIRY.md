# Alert expiry

IMPLEMENTED: minimum of attention-set deadline, event deadline, attention timestamp plus max_age_ns, source observation plus max_age_ns when known, and semantic evidence deadline when used. Default max age 500ms; configuration cannot increase it above 500ms. Exact deadline is expired.

Checks occur before rendering, at presenter submission with a newly sampled media-mapped processing clock, and at explicit pending-slot consumption. In realtime, media observation time plus elapsed time since replay due time is authoritative. Offline replay uses observation time and is labeled OFFLINE_REPLAY_PRESENTATION. It is not a realtime qualification run.

Wrong-session/out-of-order/invalid decisions are dropped. Explicit reset cancels pending state on seek/session replacement. No queue backlog can accumulate. A future asynchronous audio adapter must cancel on reset, report actual busy state and recheck deadline at playback; accepting text is not acknowledgement of sound.

PROVISIONAL: thresholds. UNVALIDATED: reaction-time adequacy. Do not relax expiry to make a stale demonstration appear useful.
