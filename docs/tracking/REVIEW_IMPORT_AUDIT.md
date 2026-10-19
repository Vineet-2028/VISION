# Task007 review import audit

**Scope update:** the user subsequently accepted this as prototype data and authorized
removing unusual labels while deferring refinement. The correction gate below is
historical; current prototype acceptance is documented in
[Task007 prototype closeout](../research/results/task007-prototype-accepted-2026-10-18.md).
It does not convert this dataset into independent qualification ground truth.

Date: 2026-10-18. The user's saved `sentinel-track-review.json` was read without
alteration. SHA256: `30274c62df21b03c3171cdfe6eec21bea9deb6874e91eb748eaad459dce67337`.

Structural validation passed for all 300 frames, including frozen frame/source/time
identity, image hashes, box bounds and unique IDs within each frame. All frames are
marked REVIEWED_TRACK_ID. Structural validity does not establish annotation accuracy.

Comparison with the generated draft found:

- 12,039 boxes in each file; no annotation changed in any frame.
- No class, box, occlusion annotation or track ID changed.
- Scene labels: six TRAFFIC, 294 UNKNOWN.
- Camera motion: five LOW, one MEDIUM, 294 UNKNOWN.
- All 12,039 occlusion labels remain UNKNOWN.

Unchanged annotations alone do not prove that review was skipped. However, an actual
image spot-check identifies an unresolved error: editor frame **39**, image
`clip-1-0038`, track **60**, is labeled TRAIN at approximately
`[0.47,375.15,766.90,873.56]`. The image shows a foreground car/SUV occupying that
region, partly occluded by a person, not a train. Correct its class and visible box,
then check its identity against neighboring frames. Frame 40 also contains a TRAIN
proposal (ID 87) in the foreground vehicle region and requires inspection.

The user subsequently confirmed looking through the frames and accepting them
unchanged. That statement is retained as review provenance; it does not resolve
the visually confirmed class error. A targeted list of 31 TRAIN boxes across
29 editor frames is saved locally in `benchmark-results/task007/train-review-candidates.csv`.
The list identifies inspection candidates, not 31 proven errors.

Both cached evaluation commands completed after structural validation: 30 runs per
detector. Their private JSON/CSV artifacts are retained as diagnostics only. No result
from this import is approved as qualification evidence. Generated proposal agreement cannot justify tracker
selection when known class/identity errors remain in the reference annotations.

To continue, open the existing local editor, **Resume** the saved review, jump to
frame 39, correct the foreground vehicle, and inspect adjacent frames for its stable
ID. Review all other proposed labels and temporal links, not just the checked box.
An edit invalidates that frame's reviewed flag; mark it reviewed again after checking.
Save a corrected export and replace the local `sentinel-track-review.json` only when
ready. Preserve earlier exports separately if desired. Do not regenerate the packet.

**TASK007 COMPLETE: NO. ENGINEERING QUALIFIED FOR TASK008: NO.**
Current blocker: **HUMAN_TRACK_GROUND_TRUTH_CORRECTION_REQUIRED**.
The existing implementation/verification evidence and architecture assessment remain
valid; this is a ground-truth quality problem, not an environment installation issue.

Verification after this import: `npm run verify` passed again with 420 tests,
static checks, builds, dependency-security policy and production smoke checks.
The policy still allows the five previously reviewed development advisory entries;
it is not a zero-vulnerability claim. Documentation formatting and `git diff --check`
also passed. No tracker implementation or submitted annotation file was changed.
