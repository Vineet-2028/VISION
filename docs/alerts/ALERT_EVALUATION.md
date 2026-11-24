# Alert evaluation and Task018 input

IMPLEMENTED recording schema12 adds optional alert_output_set to existing frame_result. It retains identity/timing, world_state, corridor_analysis, trajectory_set, interaction_analysis, risk_assessment_set and attention_decision_set from schemas6–11. Enabled manifest is12; older disabled records retain their prior schema. AlertOutputSet schema1 contains session, timestamp, mode, outputs, upstream expired candidate count and provenance. Each output joins AlertIntent and optional AlertPresentation. Suppressed attention remains in attention_decision_set, never promoted into alerts.

Task018 must join session/entity/event/episode/source timestamps and hashes; distinguish missing data, unavailable age, suppression, expiry, invalidity, rendering and sink acceptance. It must evaluate source/proxy event -> interaction -> risk -> attention -> valid alert -> presentation using common event denominators. Frame/update/entity counts are not interchangeable. Never multiply Task0145.8% and Task0163.98% or treat synthetic tests as source event coverage.

Prepare critical-event coverage, false/missed-event proxies, repeat/alert burden, first alert timing, source result age, late/expired rates, component/pipeline latency and throughput. Ground-truth source event denominator and independent human judgments remain UNVALIDATED. Task017 supplies instrumentation and raw records; Task018 is not started.

The 30-window packet extends the existing Task016 packet in a new directory, preserves attention data and adds alert timelines. All labels are null/DRAFT_REVIEW_REQUIRED. Questions: understandable? too long? too vague? useful direction? too urgent? prefer silence? Enter feedback in notes; exports are unadjudicated. No blind/low-vision feedback is claimed.

From repository root:

```powershell
apps/perception-lab/.venv/Scripts/python.exe tools/alert_review.py --packet benchmark-results/task017/review-packet-qualified --serve
```

Open http://127.0.0.1:8917 while running; Ctrl+C stops it. Loopback GET/range only, no upload or directory listing. The packet explicitly says OFFLINE REPLAY. Original packets and annotations are not modified.
