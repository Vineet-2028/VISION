# Realtime latest-state scheduler

Enable `realtime_rescue: true` only with `mode: REALTIME`, `queue_capacity: 1`
and `drop_policy: LATEST_FRAME`. Blocking debug recording and rendering are rejected
for this path. Per-component `intervals_ns` remain explicit configuration.

Acquisition is paced using the original media PTS mapped to a monotonic anchor.
It replaces a pending frame rather than accumulating work. Native frames already
more than 50 ms behind acquisition time are discarded before RGB conversion.
This is a conversion-work budget, not an extension of any alert expiry threshold.
The end boundary is still decoded so a long source terminates at the requested
interval. No source timestamps or sequence numbers are rewritten.

Accounting is explicit: pipeline `frame_counts` describe frames delivered to the
pipeline; `acquisition.decoded_in_window`, `pending_replaced` and
`skipped_before_conversion` describe acquisition work and discards. They are
different counters and must not be silently compared as identical populations.

Worker counters report submitted, pending-replaced, completed, output-replaced
and cancelled jobs. Queue/compute distributions are bounded recent-window
statistics. Delivered-result age distributions cover consumed results only.

Shutdown cancels pending work and joins in-flight native calls before closing
providers. A native call that never returns cannot be safely killed by a Python
thread; process isolation/timeouts would be required for that fault model.
