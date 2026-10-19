# Benchmark interpretation and artifact v1

## IMPLEMENTED

Every session summary includes observed source/decoded/accepted/processed/dropped/
failed counts and per-reason drops. Failed is an overlapping count of source issues
and failed processing; a recoverable component failure can still produce a frame
result. Source FPS is `(valid_observation_count-1)/source_span`. Decode, processing
and effective output FPS use count/session monotonic elapsed time, including pacing,
queueing and recording. They are not isolated model throughput.

Decode, conversion, queue, preprocess, scheduler, component, postprocess,
decode-to-result, record and optional render distributions report lifetime
count/min/max/mean and deterministic nearest-rank P50/P90/P95/P99 over the last
`metrics_window` samples. The artifact explicitly labels percentile_scope and
window_count. Empty stages report null, not invented zero latency. Do not interpret
recent-window percentiles as whole-session percentiles or sum stage percentiles.

Decode timing includes each packet decode call once; additional frames released by
that call cannot be individually attributed and have small delivery intervals.
Decode-to-result includes conversion and queue residence, but excludes later recording
and rendering. It is not scene-to-alert latency: no synchronized capture clock,
alerts or inference model exist. Realtime media playback anchoring is not a sensor
clock mapping. Compare offline runs for throughput; realtime includes pacing.

Recording is explicit. Artifact version 1 has `manifest.json`, `frames.jsonl`,
`metrics.json`. Manifest includes UUID, source ID/type, normalized configuration
and hash, calibration snapshot/hash (without free-text metadata), software/runtime
versions, safe OS/CPU count, summary and termination reason. Git revision is nullable;
Git is not required. No username, hostname or private filename is exported.
RUNNING on disk denotes an interrupted/incomplete run, not success.

JSONL lines are schema_version=1, type=event or frame_result; identity remains
unchanged and timing is processing-clock metadata. Frame results contain separate
optional component outputs, execution records, sanitized errors and provenance.
No-op outputs are null, never synthetic detections. To compare deterministic runs,
compare identities, outputs, provenance and scheduling decisions; exclude UUID,
machine metadata and measured processing timings. Replay requires original local
media plus configuration/calibration: JSONL is not a video reconstruction format.

No measured performance budget or RSS/GPU-memory result is claimed. The 5,000-frame
unit test checks bounded references/state, not production RSS or GPU allocation.
GUI copies and debug image bytes are opt-in; they change measured throughput.
Generated results are ignored by Git. Output uses a new exclusive UUID directory,
never overwrites prior sessions; users must choose a trusted local output root.

## PLANNED / RESEARCH

Hardware memory diagnostics, warmup/fork protocols, GPU synchronization, full-session
histograms and dedicated benchmark comparison tooling need separate evidence.
Record codec, hardware, warmup, failures and all distributions before setting budgets.
