# Segmentation evaluation and human review

Milestone status (2026-10-21): Task010 engineering is accepted for local prototype development with human validation deferred. This does not mark masks reviewed or waive the evaluator's ground-truth checks. The following review remains necessary for accuracy qualification.

The bounded packet contains 96 existing SENTINEL_FIRST_PERSON_V1 frames: 32 each from TRAIN_DEV, CALIBRATION and TEST. Original image hashes, sequence IDs, observation timestamps and split boundaries remain unchanged. Selection is evenly spaced within each existing split, not based on model success. These frames share one parent recording; they do not establish generalization to new users/cameras. Scenario metadata remains UNKNOWN where not reviewed.

All proposals are DRAFT_MODEL_ASSISTED. Detection/track review does not approve segmentation masks. All human mask pixels start IGNORE=255. In the local editor, accept a correct connected proposal region, change a region's class, paint or draw polygons, mark UNKNOWN when appropriate, or erase to IGNORE. Inspect boundaries and visible obstacles, then mark that frame reviewed. There is no bulk-review operation. Export progress regularly; use Resume to reload it. There is no automatic save or upload.

Open from the repository root (after packet preparation):

```powershell
Start-Process .\benchmark-results\task010\review-v1\review.html
```

Save the exported file as `benchmark-results/task010/review-v1/sentinel-semantic-review.json`. Then:

```powershell
& .\apps\perception-lab\.venv\Scripts\python.exe tools/evaluate_semantics.py --draft benchmark-results/task010/review-v1/draft.json --review benchmark-results/task010/review-v1/sentinel-semantic-review.json --output benchmark-results/task010/reviewed-evaluation.json
```

The evaluator rejects drafts, identity changes, wrong taxonomy, altered image hashes, invalid RLE and empty reviewed support. It cannot prove that a reviewer inspected pixels. Partial labels are supported; ignored pixels never enter denominators. Evaluation reports per-frame/per-split confusion matrices, per-class IoU/precision/recall/Dice, pixel accuracy, potential-traversable precision/recall, false potential-traversable counts, obstacle-as-ground errors, ground/bottom-ground recall, unknown fraction and one-pixel-tolerance boundary F1. Ignore boundaries are excluded. A missing predicted boundary scores zero when a reference boundary exists.

First-person accuracy, false-traversable evidence and boundary quality remain UNVALIDATED until this review. Disagreement between models is uncertainty research, not accuracy. Low-light, crowd, motion, shadow, stairs and texture claims require reviewed scenario labels; do not relabel brightness or model predictions as truth. Native/export parity is a numerical check, not a quality benchmark.

No training is performed. Future consented, reviewed hard cases can extend the manifest; keep qualification sequences frozen and separate from fine-tuning. Active-learning priorities may use disagreement, unknown areas and boundary failures, but no service is implemented. Model selection must consider false traversable evidence, coverage, boundary quality, latency and rights; latency alone cannot qualify a primary model.
