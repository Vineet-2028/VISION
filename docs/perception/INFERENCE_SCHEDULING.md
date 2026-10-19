# Source-time scheduling

## IMPLEMENTED

Each enabled component has an explicit positive interval in nanoseconds. The first
accepted processing observation anchors its cadence. At time t >= next_due it runs
once, then advances next_due by `(floor((t-next_due)/interval)+1)*interval`.
Missed slots are skipped; no catch-up inference burst or accumulated drift occurs.
VFR timestamps drive eligibility; frame index modulo arithmetic is never used.
Duplicate/backward times fail the scheduler; source validation rejects them first.

OFFLINE_REPLAY uses PROCESS_ALL with lazy producer backpressure. REALTIME requires
a configured staleness limit and DROP_OLDEST or LATEST_FRAME. LATEST_FRAME has effective
capacity one. Every queue replacement and stale rejection has a typed drop event.
Future lookahead is separate from queue capacity. Cooperative catch-up decoding may
drop many due frames but never creates an unbounded pending queue.
Freshness/cancellation is checked again after preprocessing, before each component
and before result publication. A non-preemptible call may overrun the limit; its
stale result is discarded rather than published as fresh.

Callbacks cover FrameDecoded/Accepted/Dropped, ComponentStarted/Completed,
FrameCompleted and SessionCompleted. They are synchronous and exceptions are fatal
unless a component deliberately raises a RECOVERABLE LabError. Source-time
scheduling is deterministic offline; realtime drops depend on actual compute speed
and are not promised to match between machines.

## PLANNED / RESEARCH

Future schedulers can replace the eligibility object with explicit queue/latency
inputs. Battery, thermal, risk urgency and adaptive rates are not implemented.
Asynchronous adapters must preserve original identity; they must never relabel a
late result with the latest frame. Separate streams will need explicit alignment.
