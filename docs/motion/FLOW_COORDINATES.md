# Flow coordinates and time

IMPLEMENTED: FramePair binds session, source clock, ordered identities A/B, calibration hash, image identity, dimensions and maximum gap. B must have a later sequence and source timestamp; timing provenance must match and be known. dt is source nanoseconds, never processing time or assumed 30 FPS. Processing start/end are separate monotonic fields.

Sparse coordinates are ORIGINAL_CAMERA_CONTINUOUS_EDGES. OpenCV integer-center coordinates are shifted by +0.5 before mapping. Both endpoints pass through the inverse Guardian ImageTransform. Their difference consequently rescales and rotates correctly; a ten-pixel processed displacement at half scale becomes twenty camera pixels.

Dense vectors are processed-image pixels per pair. DenseFlowField retains its mapping and restores sampled endpoints rather than expanding a full-resolution map. Forward/backward error thresholds are in processed pixels for both providers, not a calibrated probability. Invalid/nonfinite native samples are filtered; no outside-image sample is presented as valid.

Regression tests cover resize and crop, forward/reverse image inputs, variable dt, incompatible clock/pair rejection and immutable storage. Providers are single-owner. New sessions require a new adapter; no cross-session buffer reuse.
