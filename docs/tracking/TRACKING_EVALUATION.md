# Tracking evaluation and review

IMPLEMENTED packet: three 20-second windows at 50, 230 and 450 seconds of the existing
user-owned video, sampled at 5 FPS using authoritative PTS. These are TRAIN_DEV windows
of one recording; they are not independent clips or held-out tracking qualification.
They sample different temporal locations, but crowd/turn/occlusion coverage requires
human labeling and is not assumed. No Task006 labels/results are rewritten.

All 300 frames have DRAFT_TRACK_LINK proposals. Persistent ID ground truth requires
REVIEWED_TRACK_ID on every frame. `validate_review` binds source, ordered frame IDs,
PTS, dimensions, relative image paths and hashes to the immutable draft. Duplicate
IDs within a frame, out-of-bounds boxes and unreviewed exports are rejected.

Review policy: keep an ID for the same visible object through short occlusion when
identity is defensible; use a new ID on uncertain re-entry. Never transfer IDs across
clips. Resolve crossing/adjacent-object ambiguities using neighboring frames; do not
assume proposal links are correct. Correct boxes and classes, delete false positives,
add missed objects and label visible occlusion. Include small visible P0 objects but
do not invent boxes for fully hidden objects. Keep class ambiguity explicit in review
notes and avoid claiming unsupported identity. Unknown scene/motion labels stay UNKNOWN.

The local HTML editor supports ID/class changes, add/delete/redraw boxes, occlusion,
scene/motion labels, frame navigation, save/resume and individual frame approval.
It does not bulk approve. Files remain local and ignored; no images are uploaded.

Metrics: per-frame class-aware IoU≥.5 matching maximizes valid match count, then
overlap. Count switches across successive matched observations of each truth ID and
fragmentation when a previously matched visible truth track is missed then rematched.
Global one-to-one ID assignment maximizes matched observations; report identity
precision/recall/F1 with denominators. Additional counts include false track IDs,
duplicate observations, mostly tracked/lost and matched IoU. This is an explicitly
defined metric implementation, not official MOTChallenge/TrackEval/HOTA output.
Hand-computable tests cover switches, misses, duplicates and empty cases. HOTA is not implemented.

Confirmed and LOST predicted snapshots are evaluated; tentative states are excluded.
This deliberately penalizes ghost predictions. Matching is bounded to 512 IDs per
clip; larger packets require splitting evaluation rather than silently truncating IDs.
No real identity score is computed from draft labels. Runtime-only reports expose null
metrics. Human review is required before final tracker selection or Task008 approval.

Run preparation/validation and continuation commands in `datasets/tracking_v1/README.md`.
Keep synthetic analytical evidence separate from real reviewed metrics. Future testing
of tuned settings requires untouched clips; the current packet is development data.
