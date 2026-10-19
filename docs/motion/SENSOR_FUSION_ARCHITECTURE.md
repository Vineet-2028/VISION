# Sensor fusion architecture

## IMPLEMENTED

The temporal layer remains inside the existing guardian-core module. It has no
runtime dependencies, direct clocks, Android/Spring APIs, I/O or background threads.
Task 002 vector/quaternion/transform math and Task 003 calibrated geometry remain
the underlying contracts. Java 8 source/API/bytecode compatibility stays enforced.

The current deterministic path is:

    adapter observations -> bounded histories -> explicit temporal alignment
      -> nominal gravity compensation / gyro propagation / filtering
      -> timestamped derivatives / explicit kinematic predictions

This is not full inertial navigation, tracking, a Guardian runtime or hazard policy.
Orientation alone cannot provide translation. Synchronizer never supplies a fabricated
zero position. Pose history consumes externally supplied pose estimates.

Immutable observations/results may be published for concurrent reads. Buffers,
histories, filters and estimators have one owner thread, including their readers;
cross-thread callers must dispatch to that owner or publish snapshots. No concurrency
collection or synchronized global state is needed. Each stateful utility exposes reset.

On clock/sensor/camera restart, calibration change, large discontinuity or pose jump,
the adapter resets related state as one lifecycle operation. Cross-clock/frame input
fails rather than implicitly carrying state into a new session. Maximum gaps and
nearest/interpolation limits are caller policies, not hardcoded safety thresholds.

Quality is separate from hazard risk: unavailable inputs remain absent; temporal
ALIGNED means each requested stream has exact/interpolated data, not that its sensor
accuracy is good. DEGRADED includes partial or nearest data. Original observations,
confidence and uncertainty remain available in alignment results. Derived uncertainty
is unknown where the core cannot justify propagation.

## PLANNED

V1: validated adapter-provided orientation (potentially Android rotation vector)
plus raw gyro for bounded short-term propagation. Characterize its errors first.
No Android sensor integration is added in this task.

V2: complementary orientation fusion if evidence warrants it. Gyro captures rapid
rotation but drifts; accelerometer gravity can provide low-frequency tilt reference
only when linear acceleration is sufficiently controlled. Gravity alone does not
observe yaw. Do not blindly treat dynamic acceleration as gravity.

V3: error-state EKF only after measurement/noise/time characterization. Possible
nominal state is position, velocity, quaternion, gyro bias and accelerometer bias.
The error state and correction/reset conventions need dedicated derivation and tests.
No full ESKF or generic matrix framework is implemented.

## RESEARCH

Phone IMU-only position/velocity integration accumulates bias and orientation errors;
it needs visual/external correction for useful sustained navigation. Future visual-
inertial work may combine optical flow, feature motion and depth. No SLAM framework
or optical flow is implemented here. RND-IMU and RND-MOTION experiments record
unmeasured questions; no validated sensor accuracy or assistive safety claim exists.

The [quaternion/ESKF research reference](https://arxiv.org/abs/1711.02508) informs the
future error-state design, not an implemented estimator.
