# Frame lifecycle and clocks

## IMPLEMENTED

Local file handle -> PyAV demux/decode -> explicit RGB24 conversion -> immutable
NumPy view/array -> bounded queue -> preprocess + Java ImageTransform -> source-time
scheduler -> separate configured components (NoOp by default) -> FrameResult -> optional JSONL/viewer.

Observation time is integer floor(PTS * rational time_base * 1e9), with <1 ns
quantization. PTS may be CFR or VFR; no guessed FPS generates a replacement.
Missing, negative, overflowing, duplicate or nonmonotonic timestamps are dropped
with INVALID_TIMESTAMP. Forward gaps are preserved, including their scheduler
consequences. Discontinuous epochs require a new session; no silent rebasing occurs.
Media presentation time is a source timeline, not verified camera exposure midpoint.
It cannot enter synchronized physical fusion without measured provenance/mapping.

Negative media timelines are explicitly unsupported. Decoded corrupt frames are
CORRUPT_FRAME; a recoverable invalid packet is one DECODE_FAILURE issue whose number
of lost frames is unknown. Other decoder errors are fatal. Counts describe observed
source items, not a claimed complete inventory of corrupt encoded frames.

Start/end selection sequentially decodes from the beginning and filters PTS; it
does not perform compressed seeking or renumber/rebase observations. A future
keyframe seek must decode forward and verify alignment. No frame-accurate random
seek is claimed. End is exclusive; the first boundary frame is counted USER_SKIP.

Decode/process timestamps use the high-resolution monotonic `perf_counter_ns`;
they never replace or subtract from
media timestamps. Result identity includes source, sequence, observation ns and
provenance. Scheduled skips are not frame drops: the frame still produces a result.

The decoder owns native packet/frame buffers. Conversion creates the needed RGB
array once; frame pixels become read-only. Identity preprocessing shares it; crop
and layout transpose are views. Resize/color conversion and letterbox allocate only
for configured operations. Exact integer resize/padding geometry is composed using
core ImageTransform. With source_scaling, mapping begins at the original calibrated
image, through the explicitly scaled source, to model input; inverse returns original
calibrated pixels. No geometry is reimplemented in Python. No implicit tensor
normalization is performed; dtype is uint8 and layout is explicit.

Only the current frame, bounded queue, one lookahead and decoder working set are
retained. Session metrics retain a bounded recent window; results stream to disk.
Caller-provided adapters/listeners must not retain inputs indefinitely. Clearing
references releases arrays; native container/file handles close at EOS/cancel/failure.
The JVM is process-scoped and exits with Python, not restarted per session.

## PLANNED / RESEARCH

Pooling, zero-copy hardware decode, YUV tensor paths, calibrated sensor timestamps,
decoder subprocess isolation and hardware cancellation need measurements. Native
local decode and a component call are not preemptible mid-call; cancellation is
checked between bounded replay steps. No remote stream or live camera is supported.
