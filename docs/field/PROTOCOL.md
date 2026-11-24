# VISION field protocol V1

Status: transport implementation under integration; not a qualified field-test release.

The desktop boundary is direct Python HTTP. Spring does not relay camera bytes.
Every API request requires an ephemeral bearer token of at least 32 ASCII characters.
Use loopback HTTP for USB `adb reverse`; LAN listeners require TLS. The Android
network security policy permits cleartext only for localhost and 127.0.0.1.
Tokens stay in memory. Do not put them into URLs, logs, screenshots or source control.

## Clock contract

Android camera timestamps must use `SENSOR_INFO_TIMESTAMP_SOURCE_REALTIME`.
Capture, encode and send timestamps use `elapsedRealtimeNanos`. The host uses the
same `perf_counter_ns` clock as the existing inference pipeline. Wall time is not
used for freshness. All wire nanosecond timestamps are decimal strings.

1. POST `/v1/session` with `VISION_FIELD_PROTOCOL_V1`, client version, random
   session-scoped device identifier, mode, dimensions, JPEG format and capabilities.
2. POST `/v1/sync/start` with client `t0`; receive challenge, `t0`, host `t1` and `t2`.
3. Immediately capture client `t3`; POST `/v1/sync/finish` with the challenge and `t3`.
4. Retain the server-issued sync version, offset and uncertainty. Refresh at five
   seconds; sync expires after fifteen seconds. Uncertainty includes half RTT and
   a conservative 1000 ppm drift allowance. Above 100 ms, reject the clock sample.

Host capture is conservatively mapped to the earliest possible host time. Neither
network delay nor resynchronization makes an old observation fresh. Camera frames
at or beyond 500 ms source age are rejected before inference admission. The
Android alert policy independently rejects a deadline beyond source time + 500 ms.

## Binary camera frames

POST `/v1/frame`: four-byte big-endian header length, UTF-8 JSON header, then JPEG.
Header limit: 4096 bytes. JPEG limit: 512000 bytes. No base64 encoding.
The gateway accepts a single baseline JPEG scan and validates its encoded pixel
dimensions against the header before passing bytes to a native decoder. Truncated
payloads, concatenated images and unsupported JPEG profiles are rejected.
Header fields are defined by `FrameHeader` in `field_protocol.py`. Duplicate JSON
keys, nonfinite numbers, invalid clock order, changing session dimensions,
duplicate/decreasing sequence and decreasing camera timestamps are rejected.
The inference adapter verifies decoded dimensions again before handing pixels to Guardian.

The gateway has one replaceable pending frame. The inference adapter must own at
most one active frame. It must preserve the mapped capture timestamp, reject old
session results and never anchor the first capture to arrival time.

## Observation and recording

- GET `/v1/status`: snapshot only; polling never extends phone liveness.
- POST `/v1/recording`: `{ "enabled": true }` or false. Off by default.
- POST `/v1/event`: enumerated developer scenario START/END markers.
- GET `/v1/export`: ZIP with manifest, events JSONL, metrics JSON and metrics CSV.
- POST `/v1/close`: discard pending input, current result and clock samples.

One active session is allowed. A new start cannot silently replace it. At three
seconds without client activity the dashboard hides the result. Browser age also
advances independently of polling so stalled requests cannot freeze freshness.
The server recomputes result age from the original admitted host capture timestamp
on every response and hides the scene at 500 ms. Publication accepts only matching
session/sequence/capture tuples from a bounded eight-entry admission history;
duplicate, regressing, expired and future results are rejected. Result snapshots
do not share mutable scene payloads with the publisher or other responses.
Clock resynchronization cannot move an admitted host capture timestamp backwards;
such frames are rejected rather than clamped or assigned a fresh arrival time.
Session recording stops explicitly at 10000 events. Exports contain no images,
audio, hardware identifier or automatic human-validation label.
Closing a session disables recording and rejects late events.
Clock synchronization, recording, scenario markers and close requests carry the
session ID returned by the handshake. The gateway compares it with the active
session under its lock, so a delayed request from an old connection cannot mutate
or close the next session.
A client idle for more than three seconds loses its session on the next gateway
operation. A new handshake discards the pending frame, creates a fresh session
identity and requires a new clock exchange. Export compression runs outside the
gateway admission lock.

HTTP concurrency is bounded to eight requests, with two-second socket timeouts.
Only exact loopback web origins on port 3000 receive CORS permission. Cross-origin
requests, ambiguous lengths, chunked bodies and oversized payloads are rejected.

## Runtime integration

The field worker verifies the frozen profile, loads the models in a separate
process and publishes fresh results with the original session/capture identity.
The Android client rechecks speech deadlines and reports callback events on
`POST /v1/speech-event`. The browser reads scene snapshots independently. See
the [field guide](../releases/VISION_ALPHA_V1_FIELD_GUIDE.md) for the launch
commands. Physical camera timing, Bluetooth delivery and participant usefulness
each require independent evidence.
