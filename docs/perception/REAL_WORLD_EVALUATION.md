# Local real-world detector qualification

Task 006B has a local export/import/validation workflow. An empty manifest or
unreviewed model output is not ground truth. No real-world dataset has yet been
qualified. The 36-image COCO set remains `DIAGNOSTIC_PUBLIC_SUBSET`, reported as
`PUBLIC_DIAGNOSTIC`. Never rename it as walking-video evidence.

## Dataset acquisition review — 2026-10-15

| Source                                                        | Relevance                                                                                  | Current limitation                                                                                                                                                                                                                       |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [JRDB](https://jrdb.erc.monash.edu/dataset/)                  | Robot-height indoor/outdoor pedestrian scenes, moving cameras, crowd/occlusion annotations | Published site terms identify CC BY-NC-SA 3.0. Product research permission requires review; pedestrian annotations do not establish exhaustive vehicle ground truth. No media acquired.                                                  |
| [Ego4D](https://ego4d-data.org/docs/start-here/)              | First-person footage with diverse activities                                               | Official access requires an executed agreement and issued credentials (publisher estimates approximately 48 hours). No credentials or executed agreement are available. Its annotations must also be checked for exhaustive P0 coverage. |
| [BDD100K](https://github.com/bdd100k/bdd100k/discussions/130) | Road objects and diverse lighting                                                          | Official maintainer distinguishes code license from data license and directs commercial users to request permission. Driving perspective differs from walking. Not acquired through third-party mirrors.                                 |

These are source-specific limitations, not a claim that no usable dataset exists.
No accounts were created, license agreements signed, or personal information
submitted on the user's behalf. No user footage was uploaded. Required next input
is a usable, appropriately licensed subset with annotations or footage that can
be annotated locally. Do not evaluate unannotated classes as false positives.

## Small local workflow (PowerShell, repository root)

Use only approved local media. Supply actual source and license references:

```powershell
$python = '.\apps\perception-lab\.venv\Scripts\python.exe'
& $python tools/evaluation_dataset.py export --video datasets/raw/walk01.mp4 --output datasets/evaluation/walk01 --sequence walk01 --source 'Actual source reference' --license 'Actual permission reference' --split TEST --fps 2
& $python tools/evaluation_dataset.py import-coco --manifest datasets/evaluation/walk01/manifest.draft.json --annotations datasets/evaluation/walk01/annotations.coco.json --output datasets/evaluation/walk01/manifest.imported.json
& $python tools/evaluation_dataset.py validate --manifest datasets/evaluation/walk01/manifest.imported.json --annotations datasets/evaluation/walk01/annotations.coco.json
```

The export uses actual presentation timestamps and picks the first frame at or
after each anchored sampling deadline. Gaps never cause duplicate frames. Drafts
have `annotations_reviewed=false`, unknown scenario labels, and permission review
pending. Import preserves those gates. A reviewer must examine all P0 boxes and
negative frames, set per-frame review status, record source permission, and label
lighting/motion/occlusion/environment/blur with provenance before validation passes.
Model-generated annotations alone must never be marked reviewed.

COCO import matches exact exported filenames and dimensions, converts xywh boxes
to original-camera continuous edges, and maps category names rather than assuming
category IDs. Unsupported non-P0 classes are excluded explicitly. The strict
version-one schema is owned by `perception_lab.evaluation_dataset.EvaluationDataset`;
the older single-frame schema is a separate interchange format, not this manifest.

For multiple clips, merge sequence/image entries while retaining unique IDs and
paths relative to the resulting manifest. Use one consolidated original annotation
file and its SHA256. Keep each entire sequence in CALIBRATION or TEST, never both.
The validator rejects exact duplicate image hashes, duplicate observations and
duplicate boxes. It cannot detect near-duplicate scenes, prove annotation completeness,
or independently verify legal permission. Review those manually. Targets are
10–20 sequences, 250–500 sampled frames and at least 600 P0 objects where feasible;
do not fabricate instances or count generated fixtures toward those targets.

## Evaluation policy

Use `--annotations <source-annotations.json> --split TEST` with
`python -m perception_lab.detector_benchmark` for real-world manifests. Validation
runs before model construction. All frame hashes/dimensions and annotation-source
hashes must match. Benchmark predictions remain ignored local artifacts.

`tools/qualify_detectors.py` consumes successful hash-bound benchmark reports. It
compares observed 0.01-spaced thresholds up to 0.95, reports unavailable score
ranges, uses exact frame/object denominators, and writes CSV/JSON/SVG curves.
Fixed-FP selection maximizes recall without exceeding the budget. Fixed precision
also maximizes recall; fixed recall minimizes FP burden. No operating point is
interpolated. Plot line segments do not assert achievable intermediate thresholds.
VEHICLE here means CAR/BUS/TRUCK/TRAIN, with bicycle and motorcycle separate.
This differs from the older broad vehicle aggregate; do not compare them unlabeled.

The current analysis is explicitly post-hoc on the same public evaluation set.
A future final real-world threshold must be selected on separate CALIBRATION
sequences, frozen, then evaluated once on TEST sequences. The current reporting
tool does not automate that frozen-threshold transfer and cannot establish held-out
qualification by itself. Real and synthetic robustness remain separate.

Frame-size buckets are normalized image-area proxies, never meters. Unknown and
derived scenario annotations must remain visible. Matched-only localization
statistics omit misses and are not ground-contact or depth accuracy.

## Timing and replay

Adapters retain loaded-image end-to-end timings, warmup excluded, and finer output
transfer, semantic mapping, coordinate restoration/detection construction, and
DetectionBatch construction stages. YOLO additionally measures resize, padding,
color/tensor conversion and NMS including vendor confidence filtering. RT-DETR's
processor preprocessing and confidence-filter/box-scaling stages remain combined;
do not publish fictitious independent measurements for them. Substage quantiles
must not be added to construct a total quantile.

Realtime metrics include `realtime_result_age` and
`realtime_detector_result_age`. Publication is defined as successful recorder
handoff, before optional debug-frame/renderer work. The age uses the replay
deadline (media PTS mapped to the monotonic anchor), never subtraction across
unrelated clocks. Detector-only ages count successful outputs, including successful
empty batches, and exclude NoOp/failure/not-scheduled frames. Percentiles cover the
configured recent window; counts/moments are lifetime. Offline replay leaves age
distributions empty. Representative long-video measurements remain required.

## Current user-owned route

Task006C supersedes the external-access dependency described above. Use
[the local dataset workflow](../../datasets/sentinel_first_person_v1/README.md).
Schema2 permits temporal segments from a shared parent only with explicit windows
and at least 60 seconds between different splits. TEST means QUALIFICATION;
TRAIN_DEV is never used for threshold selection or final scoring.
