# Task006C review quality follow-up

## Current status after user clarification

The user explicitly confirmed that the frame-37 object is a shelter and requested
a SHELTER label because the editor lacked that option. That confirmed correction
has been applied in a new `annotations/sentinel-review-corrected.json`; the original
export remains unchanged. Dataset schema3 adds SHELTER as an annotation-only context
class, excluded from P0 truth. A TRAIN prediction over it still counts as a false
positive. No shelter detector, tracking or new product behavior was introduced.
The corrected manifest was imported and validated: 12,324 P0 objects plus one
context shelter, all 458 user-reviewed flags retained. Other TRAIN boxes were not
automatically relabeled. The correction provenance is saved privately in
`reviews/shelter-correction-v1.json`. The original confirmed-error blocker below
is resolved by the user's classification. Calibration completed for all six viable
candidates; see [reviewed qualification](task006c-reviewed-2026-10-18.md) for the
current results and completion decision. The sections below retain the earlier audit trail.

The updated editor is `review-shelter.html`, with the saved correction loaded,
SHELTER available and direct frame navigation. Remaining unknown scenario labels
and potential annotation bias remain disclosed limitations.

## Earlier import and spot-check evidence

The user supplied `annotations/sentinel-review.json`. Import and structural
validation succeeded: 458 reviewed flags, 12,325 objects, unchanged frame/source
identity and valid image hashes. All lighting, motion, occlusion, environment and
blur labels remain UNKNOWN. Four frames contain semantic box/class edits relative
to the proposals (ignoring schema-default fields). Edit count alone does not prove
review quality and was not used as a rejection criterion.

## HIGH — confirmed annotation error blocks qualification

Visual inspection of TRAIN_DEV frame 37 (`e011aa64a65aa9ae-train_dev-003240`)
found a TRAIN annotation at approximately [145,320,410,668] around a concrete bus
shelter. This is a false positive, not a train. Accepting it as truth would penalize
correct detectors and reward the proposal generator's mistake. The structural
validator cannot detect this semantic error; its successful result is not label QA.

The original user export is preserved. The imported manifest was moved to
`manifest.reviewed.failed-quality-v1.json`, preventing accidental use under the
normal qualified-manifest path. No calibration/qualification inference or threshold
selection was run. No annotation was silently deleted or relabeled.

## Prepared correction handoff

`datasets/sentinel_first_person_v1/review-followup.html` loads the user's saved
annotations and adds direct frame navigation. Only confirmed-bad frame 37 was
marked pending in this separate follow-up copy; the original remains unchanged.
The private `reviews/quality-audit-v1.json` records the review hash and findings.

Recheck TRAIN boxes in frames:
37, 41, 42, 43, 52, 53, 56, 75, 93, 101, 114, 124, 126, 139, 149, 150, 160, 163,
178, 181, 188, 202, 272, 278, 280, 292, 295, 311, 312, 387, 430, 435, 439, 451.

These 42 boxes are suggestions for review, not 42 confirmed errors. This list is
not an exhaustive audit of missing objects, duplicates or other classes. Correct
the visible shelter false positive, inspect remaining boxes/misses, save a new
`annotations/sentinel-review-corrected.json`, then import and validate normally.
If the earlier pass only marked frames reviewed, a substantive box review is still
required across the dataset. A question asking about the review method is pending.

## Earlier status (superseded by user clarification above)

Annotation import/schema/image checks: PASS. Semantic spot-check: FAIL.
Review-template JavaScript syntax: PASS (`node --check`). Interactive browser QA
remains unverified due the previously reported local-file browser restriction.
Repository verification is being rerun; the earlier 381-test pass is historical.

TASK006 COMPLETE: NO. ENGINEERING QUALIFIED FOR TASK007: NO.
BLOCKER: HUMAN_ANNOTATION_CORRECTION_REQUIRED.
PRODUCTION_SAFETY_VALIDATED: NO. Task007 was not started.
