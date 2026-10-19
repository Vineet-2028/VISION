# Visual and inertial alignment

IMPLEMENTED: MotionPoseHistory bridges Task004 bounded Java PoseHistory, accepting DEVICE->LOCAL_WORLD orientations with explicit session/source time. Exact or interpolation within a bounded span is permitted; nearest/latest substitution and extrapolation are not. CAMERA->DEVICE extrinsics are mandatory.

Camera A -> world -> camera B is composed using Java RigidTransform. Relative device rotation is conjugated by the camera mount through this composition. A nonidentity mount regression verifies direction independently. The supplied zero pose translation is used only to compose orientation; it does not assert measured device translation. Gyro propagation remains Task004's responsibility.

Visual/IMU disagreement is the angular distance between rotations for the exact same FramePair. No averaging or automatic fusion is performed. Missing synchronized IMU returns IMU_UNAVAILABLE. The current user recording has no established synchronized IMU; real visual/IMU agreement is N/A, not a synthetic sensor measurement.

PROVISIONAL: global-frame pose assumption. Task004 RollingShutterModel can map physical sensor row centers to time, but Task009 does not perform row-time motion correction. Unknown readout, exposure blur and high rotation can invalidate this approximation. Future row correction must inverse-map processed points before timestamp lookup.
