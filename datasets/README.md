# Local video datasets

`raw/`, `evaluation/`, `calibration/`, `manifests/` contain local artifacts only;
their contents are ignored except directory placeholders. Do not commit real
videos or identifying imagery. Obtain appropriate consent and apply retention
controls outside Git. Nothing is uploaded by the lab.

Use the sidecar contract in `schemas/video-manifest.schema.json` and the
[format documentation](../docs/perception/VIDEO_DATASET_FORMAT.md).
Tests generate tiny synthetic videos in temporary directories. Task 006 adds
`tools/curate_coco.py` for explicit acquisition of a licensed-image COCO 2017
diagnostic subset, with source URLs, attribution metadata, image hashes and P0
bounding boxes. Media stays local and ignored. This is a biased still-image
comparison set, not Guardian walking-video validation.

`schemas/detector-ground-truth.schema.json` defines the future general frame
annotation interchange. The current COCO acquisition manifest is a separate
versioned import format consumed by `detector_benchmark`; it retains COCO IDs and
maps sparse category IDs explicitly. Unknown lighting/occlusion stays unknown.
See the dated detector research report for dataset provenance and limitations.

For Task006B video sampling, COCO import, manifests and validation, see [Real-world evaluation](../docs/perception/REAL_WORLD_EVALUATION.md). Draft annotations are never benchmark ground truth.
