# V0 rescue adversarial audit

Scope: the preserved Task 018 evidence, existing pipeline contracts and the rescue
changes. The first pass inspected the implementation without altering runtime
files. This document records engineering findings; final executed gates belong
in the dated rescue results report.

## Critical findings addressed

- **Optional-provider barriers** (`pipeline.py`): synchronous depth/flow and
  main-thread surface extraction delayed fresh reasoning. The opt-in path uses
  bounded independent workers, with surface extraction owned by the semantic
  worker. Legacy offline behavior remains process-all.
- **Stale work before conversion** (`sources.py`, `latest_source.py`): even a
  one-slot mailbox could lag while converting every obsolete decoded frame. A
  realtime-only source-clock cutoff discards obsolete conversion work and counts
  those discards. Original PTS and sequence numbers remain unchanged.
- **Cross-frame association risk** (`pipeline.py`): asynchronous results cannot
  be sampled against newer boxes. Exact-frame guards protect object depth and
  flow associations. Original identities are retained for source-level evidence.
- **Unobserved shutdown failures** (`latest_worker.py`): a provider failure after
  the final poll could disappear during shutdown. Shutdown now raises an
  unobserved error; the run fails and records it. A regression test covers this.
- **Unobserved acquisition shutdown failure** (`latest_source.py`, `pipeline.py`):
  a decoder exception after the last consumed frame could be lost when the
  consumer stopped. Close now raises an unobserved source error once, and the
  pipeline marks it fatal and increments failures. A synchronized regression
  test covers early consumer shutdown and idempotent subsequent close.
- **Evidence expiring during detector work** (`pipeline.py`): accepted optional
  evidence is checked again after detector/tracker execution. No expiry budget
  was increased.

## High findings addressed

- **Repeated polygon preparation** (`corridor.py`): profiling measured 156,569
  distance calls in the capture/reasoning diagnostic. Bounded immutable edge
  preparation and allocation-free distance accumulation replace repeated lists
  and generator reductions. A 20,000-case finite-input comparison had zero
  differences; analytic boundary/winding and cache-capacity tests were added.
  The completed 18,000-frame replay preserves all funnel and text-output counts.
- **Enrichment started after synchronous detection** (`pipeline.py`): optional
  jobs now start before detection, using the same immutable prepared input.
  Domain state remains single-owner and results retain their original identity.
- **False incomplete-window detection** (`latest_source.py`, `v0_replay.py`):
  replacement can legitimately leave the last delivered observation before the
  requested end. Completion now checks the source boundary actually observed by
  acquisition. It does not fabricate a processed end frame. The earlier failed
  measurement remains failed and is not retrospectively relabelled.
- **Uninstrumented publication tail** (`rescue_profile.py`): if known stages were
  under the freshness probe but publication crossed it, the profiler previously
  reported no crossing. It now reports `publication`; a regression test covers
  that case. This changes diagnostic attribution, not runtime expiry.
- **Synchronous trace I/O** (`rescue_trace.py`, `v0_replay.py`): realtime JSON
  serialization and disk writes run on a separate bounded 16-row writer. Overflow
  or disk failure invalidates the measurement. Tests verify flush, overflow,
  closed-writer rejection and error propagation.
- **Silent GPU fallback risk** (`edge_runtime.py`, `semantic_runtime.py`): CUDA
  opt-in checks available and selected providers and disables automatic runtime
  fallback. Nine policy tests cover missing CUDA, initialization fallback,
  TF32 disabling, CPU defaults and session reuse. Separate ORT profiling records
  actual node placement, including legitimate CPU shape/NMS nodes.
- **Queue growth/shared-state races**: one pending input and one pending output
  per worker; only the pipeline owner mutates tracking/world/reasoning state.
  Provider cleanup follows worker joins. Tests exercise replacements and errors.

## Remaining issues and limits

- Sustained CPU contention with all optional providers remains an engineering
  performance concern. Short pilots are not sufficient evidence that the 2 Hz /
  P95-under-1-second gate holds for ten minutes. See the final run comparison.
- CUDA with cuDNN 9.27 failed on both configured ONNX models. Isolated cuDNN
  9.10.2.21 executes on CUDA; disabling TF32 passes the initial FP32 parity probe.
  The dated report distinguishes full qualification from these isolated probes.
- Threads cannot forcibly interrupt a hung native inference/decoder call.
  Process isolation is required if hard shutdown deadlines become a requirement.
- Historical per-object depth fusion is unavailable. The rescue does not pretend
  an older depth map supplies a current object's distance.
- The sequential cadence study has host/load/order confounding. Its raw results
  remain visible; no causal speedup claim is based on the best short pilot alone.
- Human usefulness, physical accuracy and production safety remain unvalidated.
- The final realtime reasoning-span sum has P95 43.984 ms (earlier profile 56.769 ms). The small isolated
  16-snapshot benchmark does not characterize all later, denser world states.
  This remaining latency must not be concealed by reporting only the isolated
  benchmark. Geometry edge preparation was optimized with exact finite-input
  parity; no reasoning or quality gate was removed.
- The final no-depth run delivered 60 non-expired text outputs, all "Object."
  Only two of 188 prototype reference events reached delivery. This is evidence
  of fresh delivery, not useful guidance or hazard recall.

No new cloud service, LLM/VLM, external telemetry, model download in the runtime
path, public server binding, alert-expiry extension or Task 019 feature was added.
Experimental GPU packages and raw traces remain under ignored local artifacts.
