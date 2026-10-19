# Detector cadence and tracking

IMPLEMENTED: every processed frame may update tracking, even when detector cadence
is lower. `NO_DETECTOR_RUN`, `SUCCESS_EMPTY`, `FAILURE`, `UNAVAILABLE` and nonempty
`SUCCESS` are distinct. Prediction never manufactures a detector observation.

Configure `LabConfig.tracker` and lower the detector output floor enough to expose
`recovery_threshold`. Tracking consumes the raw low-score batch; FrameResult publishes
only detections meeting `publication_threshold`. Component execution describes the
raw detector outcome, while TrackSet records its evidence state. Empty published
detections therefore must not replace TrackSet evidence in consumers.

PicoDet research publication score remains .25; YOLOX remains .15. Recovery experiments
use .10, supported by both installed exports. This changes tracking input availability,
not the frozen Task006 qualification numbers. Both detectors use the same tracker code.

The source scheduler remains observation-time anchored. Bounded queues may skip
frames. Tracking receives the actual next timestamp and rejects discontinuities
larger than max_step_ns. No fixed 30 FPS assumption. Current synchronous native
inference/decode is not preemptible; tracking cannot make a slow detector meet a deadline.

Tracker-only distributions and mapped replay observation-to-TrackSet age are separate
metrics. Percentiles use bounded recent windows. Cached 5 FPS review data supports
5/2.5 Hz experiments only; 10 Hz cadence is measured in full-video replay, not invented
from sparse cached frames. No mobile performance claim.
