# Video dataset format

## IMPLEMENTED

`datasets/raw`, `evaluation`, `calibration`, `manifests` are local-only ignored storage.
`datasets/schemas/video-manifest.schema.json` is a portable v1 sidecar contract with
videoId, scenario tags, calibrationId, resolution, timingProvenance, lighting,
environment, notes and groundTruthStatus. No annotations or real datasets are shipped.

Tags: INDOOR, SIDEWALK, ROAD_EDGE, CAMPUS, CROSSWALK, STAIRS, CROWD, LOW_LIGHT,
HIGH_MOTION, STATIC_CAMERA. Multiple tags are allowed. Ground truth is NONE,
PARTIAL or VERIFIED; the field is provenance, not automatically verified by the lab.
Do not place personal identifiers/absolute paths in notes or IDs.

Self-contained MOV/MP4, Matroska/WebM and AVI demuxers are allowed. Video is passed
as a local file handle; network URLs/playlists and shell commands are not accepted.
Actual codec support depends on the pinned PyAV/FFmpeg build. Tests locally generate
an 8x6 lossless FFV1 Matroska VFR clip. Invalid packet loss has unknown frame count;
do not call packet failures exact missing-frame annotations.

## PLANNED / RESEARCH

Dataset catalog validation commands, consent manifests, annotation tools and ground
truth association are future work. Operational calibration uses the strict Task003
JSON loader and core validators now; no calibration fitting routine is supplied.
