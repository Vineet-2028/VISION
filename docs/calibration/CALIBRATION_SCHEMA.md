# Portable calibration schema, version 1

Task 005 implements a strict JSON importer in `apps/perception-lab` backed by the
Java core constructors. This example is not real device calibration.
JSON adapters belong outside guardian-core. No Jackson dependency is required.
All numeric values must be finite JSON numbers; dimensions are positive integers.
Unknown fields, unsupported schema/model versions and missing required fields must
be rejected by a future strict importer rather than silently interpreted.

Illustrative values below are synthetic, quality UNKNOWN, and must not be deployed:

```json
{
  "schema_version": 1,
  "camera_id": "illustrative-rear",
  "calibration_version": "illustrative-1",
  "camera_frame_id": "illustrative-optical",
  "image_frame_id": "illustrative-image-1",
  "pixel_convention": "continuous_edges",
  "resolution": { "width": 1000, "height": 800 },
  "intrinsics": { "fx": 1000, "fy": 990, "cx": 500, "cy": 400, "skew": 0 },
  "distortion_model": "brown_conrady",
  "distortion_coefficients": {
    "k1": 0,
    "k2": 0,
    "k3": 0,
    "p1": 0,
    "p2": 0,
    "max_radius": 1
  },
  "camera_to_device": {
    "version": "illustrative-extrinsic-1",
    "device_frame_id": "illustrative-body",
    "rotation_wxyz": [1, 0, 0, 0],
    "translation_meters": [0, 0, 0]
  },
  "calibration_quality": {
    "state": "UNKNOWN",
    "rms_pixels": null,
    "sample_count": null,
    "timestamp_epoch_millis": null
  },
  "metadata": "Illustration only; not a physical camera/body alignment"
}
```

camera_id plus calibration_version forms CalibrationId. Resolution, intrinsics,
distortion and frame identities are one immutable snapshot. Publish a new version
when any effective geometry changes; do not mutate or reuse an existing identity.
camera_to_device is optional (null when unavailable); when present it binds to this
same calibration ID and has its own version. Its source is camera_frame_id with
CAMERA kind and destination device_frame_id with DEVICE kind; translation is in
DEVICE meters, quaternion Hamilton w,x,y,z. Missing extrinsics must not become
identity extrinsics. The synthetic identity above is not an Android axis mapping.

Intrinsics are pixel-edge coordinates. Convert integer-center calibrations explicitly
(typically +0.5 to cx/cy when index 0 denotes the first center), record the source
convention and test the adapter. Nonzero skew is rejected. For model `none`, require
an empty coefficient object, explicitly representing already ideal/rectified images.
For `brown_conrady`, require exactly the six documented coefficients/domain fields;
max_radius is dimensionless and must satisfy the core domain validation. Unknown
families (including fisheye) fail rather than falling back to `none`.

Quality states: UNKNOWN, VALID, DEGRADED, INVALID. RMS is nonnegative pixels; sample
count is a positive integer when known; VALID requires both. Timestamp and metadata
are optional. RMS alone does not establish validity; the adapter/evaluation process
owns evidence and quality classification. No quality thresholds are invented here.
Keep focus, zoom, crop, OIS/EIS mode, source convention and fit/holdout provenance
in a future structured metadata extension. Avoid personal identifiers and images
in portable calibration files; no upload or telemetry is part of this design.

Importer tests cover missing/unknown fields,
unsupported models, duplicate keys, finite ranges, mismatched identities and schema
migration rejection. The importer is outside guardian-core; Task 003 itself has no parser.
