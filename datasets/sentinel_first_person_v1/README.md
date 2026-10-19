# SENTINEL_FIRST_PERSON_V1

Place user-owned `.mp4` files in `raw/`. Raw media is immutable, local-only and
gitignored. Do not publish footage or identify faces or plates. Other generated
directories are private by default, including annotations and review artifacts.

From repository root, PowerShell:

```powershell
apps/perception-lab/.venv/Scripts/python.exe tools/prepare_first_person.py
```

Preparation refuses tracked/unignored media, hashes each recording before and
after processing, validates increasing PTS, and writes a private inventory.
It does not approve annotations. Existing outputs are never overwritten.

For a long recording, three contiguous temporal windows use 40/25/35 percent of
the duration remaining after two 60-second guard bands. TRAIN_DEV, CALIBRATION and
TEST (the schema's name for QUALIFICATION) retain their common parent media hash.
These are correlated segments, not independent recordings. No random frame split.
Base sampling uses a 2 Hz PTS grid; review candidates have at least 3-second spacing.
An 8x8 grayscale average hash rejects candidates within Hamming distance 3 of any
previously retained candidate. This detects some near duplicates, not every re-encode.
Scenario labels remain UNKNOWN until reviewed. Selection does not inspect detections.

`manifest.draft.json` is the authoritative schema-v2 annotation draft. The private
`manifests/inventory.json` records source metadata and sampling configuration hash.
All boxes refer to original decoded-image continuous edges. Screen recordings do
not establish physical-camera calibration or exposure timestamps.

Use `tools/evaluation_dataset.py import-coco` for local CVAT/Label Studio COCO
exports; category names are mapped explicitly. Imported boxes remain unreviewed.
Review missing objects as well as proposals. `annotations_reviewed=true` means a
human reviewed the entire frame, including negatives; never set it in bulk.

After review, retain the exported annotation file and its SHA256 in the manifest.
Validate with `tools/evaluation_dataset.py validate --manifest <manifest> --annotations <review-export>`.
Use `tools/qualify_detectors.py --freeze` on CALIBRATION predictions first, then
`--frozen <artifact>` with TEST predictions. Both commands require `--annotations`,
`--dataset`, one `--runs` file, and a new `--output` path. Never revise a frozen
configuration after reading qualification metrics.

Future versions use a new output dataset directory and `--dataset-id`; preserve
V1 hashes, split assignment, annotations and results. Do not overwrite historical
evidence or register the same recording as independent new data.

## Current review handoff (2026-10-17)

**Latest update:** following your confirmation, the frame-37 shelter is now labeled
SHELTER in `annotations/sentinel-review-corrected.json`. Schema3 preserves context
annotations while excluding them from P0 truth; TRAIN predictions on shelters count
as false positives. `manifest.reviewed.json` has been imported and validated again.
Use `review-shelter.html` for any further corrections; it includes SHELTER and frame
navigation. Original exports and the failed-quality import are preserved.

**Earlier spot-check:** your saved review was imported and structurally validated, but
frame 37 contains a confirmed false positive (a bus shelter labeled TRAIN).
Open `review-followup.html` to continue from your saved work; use **Go to frame**.
The original export is preserved. See the private `reviews/quality-audit-v1.json`
for suggested rechecks. Save corrected work as `annotations/sentinel-review-corrected.json`
and use that filename in the import/validation commands below. The previous imported
manifest is retained as `manifest.reviewed.failed-quality-v1.json`, not qualified truth.

The initial preparation handoff below is retained for context:

Preparation and proposals are complete: 458 frames (182 TRAIN_DEV, 115 CALIBRATION,
161 TEST), 12,328 draft boxes, zero human-reviewed frames. Do not rerun preparation.
Open `review.html` from this directory in your local browser. It has no network
dependencies. Keep it beside `sampled_frames/`. Automated browser validation was
blocked by the agent browser's file-URL policy; Python schema/import tests pass.

For each frame, remove false positives, correct classes/boxes, add missing P0
objects, label visible scene attributes, then click **Mark entire frame reviewed**.
Use **Save review JSON** frequently; **Resume saved JSON** restores saved progress.
Review all objects, including those both models missed. Never bulk-approve drafts.
The original export is preserved as `annotations/sentinel-review.json`. The current
corrected export is `annotations/sentinel-review-corrected.json`; it has already
been imported. Validate it from the root without reimporting or overwriting:

```powershell
apps/perception-lab/.venv/Scripts/python.exe tools/evaluation_dataset.py validate --manifest datasets/sentinel_first_person_v1/manifest.reviewed.json --annotations datasets/sentinel_first_person_v1/annotations/sentinel-review-corrected.json
```

The importer rejects incomplete review, changed source identity and overwrites.
All six viable candidates have now completed CALIBRATION, frozen operating points,
and the held-out TEST comparison. See the reviewed October 18 report under
`docs/research/results/` for the provisional research selection and evidence limits.
Do not change V1 labels or thresholds in place after inspecting these results;
future development requires a new version and untouched evaluation data.
