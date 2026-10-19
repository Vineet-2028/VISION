# Tracking architecture

IMPLEMENTED: Python laboratory tracking consumes Sentinel DetectionBatch and emits
immutable TrackSet/TrackSnapshot values. Guardian Java remains authoritative for
geometry and physical/time primitives. Tracking does not import detector vendors,
Spring, web code or physical velocity classes. No depth, flow, risk, attention,
Android or world-model implementation is introduced.

`MultiObjectTracker` specifies update, reset and close. `AssociationTracker` provides
configurable IoU, motion/global assignment and two-stage policies, plus dedicated
alpha-beta and fixed-dimension Kalman estimators. These are research baselines,
not a port or dependency on SORT/ByteTrack. The designs are informed by
[SORT](https://arxiv.org/abs/1602.00763) and the low-score recovery strategy in
[ByteTrack](https://arxiv.org/abs/2110.06864). No additional runtime dependency was added.

One owner thread mutates a tracker. Snapshots contain values and bounded observation
history, never image buffers, mutable estimator arrays or model outputs. TrackId is
session plus a monotonically increasing serial, independent of detector IDs. Reset
clears state but does not recycle serials, even within the same named session.
Pipeline finalization closes the tracker on completion, cancellation and errors.

Time uses FrameIdentity source-clock/sequence/observation nanoseconds, not wall time.
The tracker additionally requires explicit session identity. Unknown timing, different
source/session/timing provenance, repeated/regressing sequence/time and excessive
step gaps reject before mutation. Discontinuous seek requires explicit reset.
Pipeline image-dimension changes fail instead of mixing incompatible coordinates.

The pipeline owns an explicit forward-gap policy: for the same source/timing with
increasing sequence, a step beyond `max_step_ns` resets tracking, emits
`TrackingGapReset`/`FORWARD_GAP_RESET`, retires prior IDs and starts tentative new
IDs. The serial counter remains monotonic. This handles long dropped-frame gaps
without extrapolating through them. Regressions or clock changes are not reset into
valid observations. Direct tracker callers still receive an error and must reset.

The tracker can operate without camera calibration. Bearing metadata stays unavailable
in V1. Image-space rates are pixels/second and cannot be used as physical velocity,
TTC, CPA or risk. Camera motion contaminates apparent object motion.

PROVISIONAL configuration: 64 active/lost tracks combined, 128 selected detections,
32 observations per track. Hard configuration ceilings are 128/256/128. Admission
sorts detections deterministically by score, category and box; overflow emits a
diagnostic. Exact/nearly identical same-category duplicates are suppressed at .98 IoU;
this deliberately avoids broad merging of nearby objects. Removed IDs appear only
in the current update, with no ever-growing retired-object store.

Only P0-mapped categories enter the tracker. Unknown detector categories do not
become P0 tracks. Session recording is opt-in; tracking records use schema2 while
legacy no-tracking records retain schema1. Recording includes bounded history and
can be expensive; tracker-only timings exclude JSON serialization.

Privacy: a track ID denotes a local temporal object, never a known person. No face
recognition, embeddings, cross-session identity, facial crops or telemetry are added.
Deep ReID is not implemented; its need remains INSUFFICIENT_EVIDENCE pending reviewed IDs.
