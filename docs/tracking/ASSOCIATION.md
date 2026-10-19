# Association

IMPLEMENTED: canonical detection order, predict eligible tracks to source time,
form bounded costs, then solve a global rectangular assignment with dummy unmatched
columns. Ascending-column ties and increasing TrackIds make replay deterministic.
The dedicated shortest-augmenting-path solver has no transitive SciPy dependency.
It is cubic in bounded dimensions; runtime caps prevent uncontrolled assignment size.

Cost = 1 − IoU + center_weight × normalized_center_distance + class_mismatch_penalty.
Center distance normalizes by predicted-box diagonal, with a one-pixel floor.
The configured displacement gate rejects distant matches. IoU-only also requires
minimum overlap; motion policies permit non-overlap only within half the center gate.
Different categories receive a penalty, not an unconditional prohibition.

Two-stage policy matches publication-score detections first. Remaining established
tracks may recover from scores between recovery and publication thresholds. Low-score
detections do not start tracks. IoU and single-stage motion baselines omit recovery.
This is a ByteTrack-like concept, not a claim to reproduce the published implementation.

Conservative duplicate suppression uses .98 IoU only within the same category;
there is no aggressive track merging. Hard gates can fragment tracks under camera
turns. Relaxing them can increase ID switches. Choose settings on development data
after review, never silently optimize against a held-out result.

MEASURED synthetic comparisons and pending real reviewed comparisons are recorded
in the dated benchmark report. No baseline is declared a real-world winner yet.
