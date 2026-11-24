# VISION_FIELD_PROTOCOL_V1

The [wire reference](PROTOCOL.md) defines the handshake, authenticated requests,
binary frame framing, clock exchange, freshness, recording and export.

After a successful handshake, send only camera captures from the active session.
Use a new random ID and a new clock exchange after reconnecting. The host checks
the frame's JPEG dimensions before native decoding. CameraX cardinal rotation
is frame-specific. A rear-camera gravity observation contributes roll only when
it is fresh, has a plausible magnitude and has observable in-plane projection.
The phone sends rotation-vector metadata separately. Neither signal supplies
user walking direction.

The worker returns scenes through the gateway. The browser polls snapshots.
The phone polls `GET /v1/alerts`, which applies the same freshness check without
serializing the scene graph. Capture-to-receive and capture-to-publication times
use conservative host mapping and include clock uncertainty. For published
alerts, phone callbacks use the original camera timestamp on the same device
clock. Export percentiles summarize only recorded samples; missing callbacks
remain unmeasured.
The phone consumes only authorized `field_alerts` with its own session ID and
an unexpired conservative host deadline. The speech event endpoint records
callbacks against previously published alert IDs. Repeating a callback does
not increment its event count. Recording is opt-in and excludes image/audio data.
