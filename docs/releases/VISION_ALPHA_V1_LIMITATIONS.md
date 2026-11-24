# VISION Controlled Alpha V1 limitations

The engineering evidence comes from one locally permitted recording. Its media
includes non-walking segments: browser inspection found an advertisement around
27 seconds. Do not classify all sampled windows as walking-scenario evidence.
The source must be screened before any scenario-specific human study. Its media
timestamps support repeatable software comparisons. The recording has unmeasured
camera intrinsics and mount pose. Distance, walking direction, acoustic latency
and the usefulness of an interruption require separate measurements.

On the full replay the text sink accepted 172 alerts before expiry, including
133 generic alerts. Generic wording deliberately preserves a physical event
when its object class lacks sufficient evidence. An accepted text event records
a software decision. It cannot establish that speech was heard or understood.

The realtime profile replaces pending frames to keep the latest capture. The
measured maximum publication age exceeded 1.5 seconds even though the P95 was
below 250 ms over the whole recording. Percentiles cannot establish a worst-case
response guarantee. The interface must expire old results and show unavailable
camera views explicitly. Silence cannot establish that a path is clear.

Rotation tests use controlled image transformations. Image-plane pan, darkening
and blur are proxies with known provenance. They cannot establish performance
on turns, low light or motion across independent people, devices or environments.
The optional neural semantic providers are research-only. The Alpha configuration
uses PicoDet FP32 and retains unknown entities in the physical reasoning path.

Controlled human review, phone camera behavior, Bluetooth audio and public use
each require their own evidence. Keep the field harness supervised and local.
Do not use the prototype as a navigation aid.
