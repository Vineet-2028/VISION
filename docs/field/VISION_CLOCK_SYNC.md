# VISION field clocks

The phone sends its monotonic time at request start and response receipt. The
gateway supplies host receive and reply timestamps. The handshake records a
versioned host-minus-client offset, round-trip time and an uncertainty bound.
The client and server must use the same exchange for a frame.

The host maps camera time to the earliest plausible host capture time using the
offset and uncertainty. It includes an additional 1,000 ppm drift allowance as
the estimate ages. A sync older than 15 seconds, uncertainty over 100 ms, a
future capture or a regressing mapped capture is rejected. Arrival and inference
completion cannot reset the capture clock. The transport and scene display use
a 500 ms freshness deadline.

The browser receives age at response time, adds the measured request duration
conservatively and advances the age with its own monotonic clock. Phone
playback must recheck expiry against the latest plausible host time at submission
and on the Android playback-start callback. Record callbacks and physical
acoustic measurements separately.

Read the [field protocol](PROTOCOL.md) for handshake, session and export details.
