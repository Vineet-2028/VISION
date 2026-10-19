# Coordinate frames and timing

| Frame       | Axes                                                               | Origin / units                                        |
| ----------- | ------------------------------------------------------------------ | ----------------------------------------------------- |
| IMAGE       | u right, v down; two-dimensional                                   | Upper-left outer edge; pixels, first center (0.5,0.5) |
| CAMERA      | x right, y down, z optical forward; right-handed                   | Optical center; position meters                       |
| DEVICE      | x right, y body-forward, z up; right-handed                        | Adapter-defined physical body reference; meters       |
| LOCAL_WORLD | x reference-right, y reference-forward, z gravity-up; right-handed | Session-fixed origin and horizontal reference; meters |

Every frame has a kind AND instance identity. New cameras, coordinate geometries
and world sessions need distinct identities. Pixel fractions and normalized camera
plane coordinates have separate types. Frame identity never supplies missing units.

RigidTransform(A,B,R,t) maps p_B=R*p_A+t_B, direction_B=R*direction_A.
Translation is meters in B. Hamilton quaternion order is (w,x,y,z), active rotation;
q2*q1 applies q1 then q2. A.then(B) applies A first then B and checks the join.
No Android axis mapping, centered camera or camera-forward/device-forward equality
is assumed. CameraExtrinsics binds CAMERA->DEVICE to a calibration ID and an
extrinsics version. DevicePoseEstimate supplies DEVICE->LOCAL_WORLD, confidence
and optional positional/angular deviations, not an IMU integration algorithm.

SpatialGeometry maps the camera optical center with the composed point transform
and the camera unit ray with the direction transform. Translation must never be
applied to the direction. The resulting Ray3D has a world origin, unit direction
and capture time; pointAt(t) uses nonnegative metric distance, not inferred depth.

FrameMetadata now optionally carries CalibrationId(cameraId,version); old unbound
Task 002 observations remain representable but cannot enter calibrated pixel/ray
operations. CameraCalibration.requireFrame checks ID, IMAGE identity and dimensions.
The producer must never reuse an ID for different lens, resolution, crop or effective
stabilization geometry. The core cannot verify a dishonestly labeled snapshot.

Pose and ground must be evaluated at exactly the exposure-midpoint timestamp on
the same monotonic clock/session as the ray. Unknown estimates return unavailable.
Timestamp mismatch throws rather than silently using stale pose. Future adapters
own synchronization and interpolation with uncertainty; wall-clock time is metadata.

SpatialGeometryTest covers nonzero extrinsic translations, rotation composition,
downward/sideways views, mismatched clocks/frames/calibration and concurrent reads.
All supplied core implementations are immutable; custom lens implementations must
also preserve frames, be immutable and bound their computation.
