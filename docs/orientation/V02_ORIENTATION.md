# V0.2 camera orientation implementation

Status: cardinal geometry and detector input boundary implemented; end-to-end orientation robustness is not yet demonstrated.

`CameraOrientationState` binds evidence to an exact source frame, including its timestamp and timing provenance. Missing orientation stays UNKNOWN. The canonicalizer rejects cross-frame metadata and source-resolution scaling that has not been explicitly composed. It accepts integer cardinal rotations only; it does not silently round arbitrary roll.

`CameraCanonicalizer` delegates pixel-edge mappings, rotated ideal intrinsics, and camera basis to the existing Guardian `RotatedIntrinsics`. It caches four immutable mappings rather than reconstructing Java objects per frame. Clockwise pixel rotation uses contiguous NumPy buffers. Source identity and timestamps survive unchanged.

The `prepare` method supplies the existing `PreparedImage` detector boundary. Vendor resizing/letterboxing composes with the original-to-canonical mapping, so inverse-mapped detections return to original camera coordinates. Do not rotate those detections a second time. The downstream world model must continue using the original calibration while operating in that original basis.

Distortion policy is inverse mapping to the original calibration. Rotated ideal intrinsics are not a claim that Brown distortion coefficients can be copied into a differently oriented camera model. A canonical-coordinate physical geometry consumer must explicitly use the corresponding basis and distortion handling.

Executed tests cover all four cardinal rotations, pixel contents, reversible point mapping, rotated intrinsics, orthonormal right-handed camera bases, source identity rejection, and composition with detector letterboxing. These are synthetic geometry tests; they do not measure detector accuracy under rotation.

## Runtime integration — November 5

`Frame.camera_orientation` optionally carries the existing timestamp-bound state.
The frame constructor rejects metadata from another identity. `FrameResult` and
replay traces retain that metadata, including when view health suppresses inference.
`orientation_canonicalization` is an explicit configuration switch, disabled by
default. The command-line and replay builders now use the same preprocessing factory.

When enabled, GOOD total received-image roll from IMU or synthetic evidence uses
`RollCanonicalizer` with an EXPAND canvas and an output pixel limit. Total roll is
not added to CameraX cardinal rotation; the sensor adapter must already express it
in received-image coordinates. Without usable total roll, GOOD cardinal metadata
uses the exact cardinal path. Missing/poor orientation leaves the image unchanged.
Pitch/yaw never become roll corrections. Color conversion remains explicit, and
unsupported combinations with crop/resize/NCHW preprocessing are rejected.

Both paths inverse-map model outputs to the original calibrated camera coordinates.
Synthetic integration tests verify that the actual pipeline receives canonical
model inputs while retaining original frame dimensions, identity and metadata.
The full perception check passed with 1,332 tests, Ruff and strict mypy for 110
production modules after integration. This does not establish real rotated-scene
detector retention, semantic consistency or physical orientation accuracy.

Still required: real timestamped phone sensor ingestion and camera-frame conversion,
full-pipeline RAW/canonicalized rotated-scene measurements, and final qualification.
Heading-informed corridor logic is implemented but needs authorized ground/mount
evidence; camera forward is not a measured user walking direction. Auto-mount remains
research and does not block the controlled Alpha. No physical-orientation or
production-safety validation is claimed.
