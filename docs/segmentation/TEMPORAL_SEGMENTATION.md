# Temporal semantics

IMPLEMENTED: OBSERVED, PROPAGATED, STALE and UNAVAILABLE contract states, with separate original observation and result identities, explicit source-time age and bounded warp count. An OBSERVED result cannot substitute another observation identity. PROPAGATED requires a later identity and nonzero age/warp count.

Default runtime propagation is deliberately DEFERRED. Frames without an observation publish no mask. No hidden inpainting or cached mask is relabeled as fresh. Future flow propagation must bind exact session, source, calibration/image grid and frame pair, preserve original observation time, mark newly uncovered pixels UNKNOWN and expire results. Flow/no-flow cannot change fresh segmentation inference.

REALTIME inference uses one worker and one in-flight job. Busy cadence ticks are skipped. A completed older observation retains its own identity; it is not fused with current detections/depth/tracks. Beyond configurable `max_age_ns` (default one second), it becomes STALE and its surface output contains only unknown evidence. Shutdown waits for native inference and releases the retained job. Native inference cannot be forcibly cancelled; shutdown duration is not hard real-time bounded.

Flow-warped consistency and age-versus-accuracy experiments require reviewed masks and are deferred. Adjacent raw pixel agreement under camera motion is not a temporal-accuracy measure.
