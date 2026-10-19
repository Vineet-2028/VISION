# Track-depth association

IMPLEMENTED policy: EXACT_FRAME or UNAVAILABLE. No stale carry-forward or temporal smoothing is enabled.

DetectionBatch and DepthFrame must have equal FrameIdentity (source/clock identity, sequence, observation nanoseconds, timing provenance). Frames from different sources/times are rejected. The pipeline owns one recording session; cross-session joining is unsupported. Source identity must identify the observation clock, not wall-clock time.

TrackSet association consumes only public immutable contracts. Observed tracks use latest_observed_bbox and must match the current observation timestamp. Predicted-only tracks receive UNAVAILABLE even when a current map exists. Unscheduled depth produces no fresh estimate.

DepthEstimate belongs to frame plus image region before any TrackId. TrackDepthObservation adds an identity association without changing the estimate. No history is transferred to new IDs, and no dense map is retained by a track. Undetected identity switches can still associate a correct per-frame sample with the wrong track identity; this implementation does not claim to repair Task007 tracking.

Future optional stale carry-forward must retain original identity and age, expire explicitly and never be represented as fresh. Future robust smoothing must preserve raw samples and must not infer physical object velocity.
