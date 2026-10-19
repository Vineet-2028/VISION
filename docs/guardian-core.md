# Guardian mathematical and domain foundation

## Ownership and audit scope

Task 002 first inspected the existing web/API, Maven wrapper, npm tooling, CI,
contracts and reserved packages. Implementation is confined to guardian-core,
its root/CI verification integration, documentation and benchmark hook. No
application code or npm dependencies need changes.

One library owns the current small set of math and observation types. Existing
geometry, perception, trajectory, and evaluation directories reserve later
orchestration; they must not duplicate these contracts. Spring Boot and web do
not depend on the core yet. No distribution abstraction or numerical dependency
is needed. Private final fields and read-only accessors expose immutable snapshots; optional fields never
use sentinel numbers. Mutable collections are deliberately absent.

## Coordinate contract

FrameId includes kind AND instance ID. Two cameras, calibration revisions, or
world sessions must use different IDs. Equality of an enum alone is insufficient.

| Kind        | Axes                                                 | Handedness / origin                                         | Units                                                                        |
| ----------- | ---------------------------------------------------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------- |
| IMAGE       | x right, y down                                      | 2D image upper-left outer edge; no 3D handedness            | Vector2 callers specify pixels or normalized values; boxes always normalized |
| CAMERA      | x right, y down, z optical forward                   | right-handed, optical center                                | meters for positions                                                         |
| DEVICE      | x right, y body forward, z up                        | right-handed, agreed body reference point                   | meters for positions                                                         |
| LOCAL_WORLD | x reference right, y reference forward, z gravity-up | right-handed, session-fixed origin and horizontal reference | meters for positions                                                         |

All Vector3 instances carry a spatial frame; IMAGE is rejected. Vector2 also
carries a frame, but does not encode its scalar units. Never mix pixel vectors and
normalized vectors. BoundingBox2D avoids this ambiguity by fixing normalized
image-edge coordinates and positive area. Pixel-edge coordinates scale as
u=x*width, v=y*height. Intrinsics use this same convention; an adapter must reconcile
a calibration's pixel-center convention and crop/rotation before use.

Vector3 arithmetic is quantity-neutral: meters, m/s, m/s², or unit directions as
specified by each API. VectorEstimate adds an explicit quantity and SI uncertainty.
Frame equality does not make different physical quantities interchangeable.

Hardware adapters supply intrinsics, distortion parameters, extrinsics and clock
alignment; Task 003 core geometry applies these calibrated inputs. No Android axis
mapping or camera-to-IMU transform is hard-coded.
DEVICE and CAMERA change pose; differentiation must use observations transformed
into the SAME fixed frame at their respective capture times. Merely relabeling
rotating camera coordinates as LOCAL_WORLD is invalid.

Quaternion is a unit Hamilton quaternion (w,x,y,z). Multiplication q2*q1 applies
q1 first, q2 second. Quaternion.rotate is an active rotation within one frame;
RigidTransform owns source/destination frame mapping. Quaternion inputs are
normalized with scaling to avoid norm overflow. Near-zero input is rejected.

## Time contract

MonotonicTime stores nonnegative elapsed nanoseconds from an adapter-owned origin
and a clock/session ID. An adapter must rebase a signed native clock; do not pass
raw Unix time or concatenate sessions. The core cannot detect a dishonestly labeled
clock. Unsynchronized clocks fail comparison and subtraction. The later timestamp's
elapsedNanosSince(earlier) permits zero for ordering and rejects negative intervals.
motionSecondsSince additionally requires at least 1,000 ns. Integer subtraction
occurs BEFORE conversion to seconds, preserving small intervals near Long.MAX_VALUE.

FrameMetadata captureTime denotes exposure midpoint; rolling shutter and timestamp
uncertainty remain research questions. ImuSample represents time-aligned acceleration
and gyro measurements; asynchronous samples require the later synchronization layer.
WallClockTime is Unix epoch milliseconds, only metadata. Algorithms do not read any
clock or use wall-clock differentiation.

## Central numerical policy

| Constant                         | Meaning                                                                    |
| -------------------------------- | -------------------------------------------------------------------------- |
| EPSILON = 1e-12                  | Dimensionless/arithmetic near-zero normalization and scalar division limit |
| MIN_DELTA_NANOS = 1000           | Minimum usable differentiation interval: 1 microsecond                     |
| NEAR_ZERO_DISTANCE_METERS = 1e-6 | Direction/radial geometry is undefined at or below 1 micrometer            |
| NEAR_ZERO_SPEED_MPS = 1e-6       | Unique future CPA/radial TTC not estimated at or below this speed          |

These are degeneracy guards, not measurement accuracy, physical speed limits or
hazard thresholds. The build keeps all source warnings fatal; only javac's
compiler-option warnings are excluded because JDK 21 deprecates the deliberately
selected Java 8 target. SpotBugs remains at Max effort / Low threshold.

Reject nonfinite inputs and nonfinite arithmetic outputs with
IllegalArgumentException. Unrepresentable derived TTC yields an unavailable result.
CPA arithmetic overflow fails explicitly; no NaN or infinity escapes. The functions
do not clamp incorrect inputs or silently claim a result. Magnitudes use hypot;
squared magnitudes can explicitly fail on overflow even when magnitude is representable.
No universal maximum human/object speed is assumed.

## Equations and semantics

All inputs to each binary spatial operation must have matching frame identities.

| Operation       | Equation                                      | Implementation                             | Assumptions / tests                                                                                                     |
| --------------- | --------------------------------------------- | ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| Vectors         | a±b, s*a, a/s; a·b=sum(ai*bi); norm=sqrt(a·a) | Vector2, Vector3                           | Finite components; divisor guard; arithmetic, distances, overflow, zero normalization, seeded invariants                |
| Cross product   | a×b=(ay*bz-az*by, az*bx-ax*bz, ax*by-ay*bx)   | Vector3.cross                              | Right-handed; basis vectors and antisymmetry                                                                            |
| Rotation        | v'=q*(0,v)*conjugate(q)                       | Quaternion.rotateInto                      | Unit quaternion; equivalent matrix without temporary products; known quarter/half turns, inverse                        |
| Rigid map       | p_B=R_BA*p_A+t_BA; d_B=R_BA*d_A               | RigidTransform                             | Translation meters in B; directions exclude translation; inverse and noncommuting composition                           |
| Composition     | T_CB∘T_BA=(R_CB*R_BA, R_CB*t_BA+t_CB)         | RigidTransform.then                        | Chain identity checked; inverse round trips                                                                             |
| Velocity        | v=(p2-p1)/dt                                  | Motion.velocity                            | Same fixed frame, positive monotonic dt; analytical components and near-zero rejection                                  |
| Acceleration    | a=(v2-v1)/dt                                  | Motion.acceleration                        | Same conditions; raw/noisy, no smoothing                                                                                |
| Relative motion | r=po-pu; vr=vo-vu                             | Motion.relativePosition / relativeVelocity | Same frame and common observation time; moving user and stationary object                                               |
| Closing speed   | c=-(r·vr)/norm(r)                             | Motion.closingSpeed                        | Positive closing, negative separating; direction undefined near coincidence; stationary/perpendicular cases             |
| Radial TTC      | t=norm(r)/c                                   | Motion.radialTtc                           | c exceeds numerical guard, nonzero range, constant radial closing approximation; NOT proof of collision                 |
| CPA time        | t=-(r·vr)/norm(vr)²                           | Motion.closestApproach                     | Constant relative velocity, unique minimum, t>=0; factored by speed to limit overflow                                   |
| CPA distance    | d=norm(r+vr*t)                                | Motion.closestApproach                     | No object radii/path uncertainty; head-on, offset, crossing, different crossing times, receding, zero and tiny velocity |
| Bearing         | atan2(right,forward)                          | Motion.horizontalBearing                   | Radians in [-pi,pi]; CAMERA uses x/z, DEVICE/WORLD x/y; undefined for vertical-only position                            |
| Direction       | r/norm(r)                                     | Motion.direction                           | Optional unit vector; no language labels                                                                                |

Past CPA returns unavailable, not a fabricated future event. Exactly t=0 with
nonzero relative velocity is a valid boundary minimum. Zero relative velocity
has no unique CPA time, so returns unavailable (current separation is still directly
available from the relative position). Coincidence with nonzero velocity yields CPA
(0,0), but no radial TTC or bearing. CPA is not a finite-size collision model.

Velocity from two positions is the interval-average velocity; its natural time
label is the interval midpoint. Callers differentiating interval velocities must
supply their correct representative timestamps, not blindly reuse an endpoint.
Relative-motion functions require co-temporal inputs; they do not align samples.

## Uncertainty and contracts

Confidence is a bounded score [0,1], not automatically a statistical probability.
Measurement uncertainty describes dispersion in the measurement's units, here
optional one-standard-deviation values. Calibrated probability requires evidence
from held-out evaluation; neither confidence nor standard deviation supplies that
evidence. Unknown values use Optional/OptionalDouble and zero confidence; known
zero-confidence values remain possible. A known value without standard deviation
means uncertainty was not provided, not zero uncertainty.

ScalarEstimate explicitly distinguishes KNOWN/UNKNOWN. DepthEstimate keeps metric
Euclidean camera range separate from producer-defined relative depth, whose sign,
scale and ordering must be documented by its source. Relative depth cannot be read
as meters. Metric range is strictly positive and is NOT optical-axis z-depth.
Conversion requires a later calibrated geometry algorithm.

VectorEstimate has optional per-axis deviations; it is not a full covariance model,
and no independence assumption or uncertainty propagation is performed. Orientation
uncertainty is an optional scalar angular deviation in radians. TrackedEntity is a
snapshot with stable session-scoped ID, latest observation time, quantities, optional
kinematics, confidence, lifecycle and count. No transitions or predictions exist.

Raw ImuSample accelerometer values are specific force with gravity uncompensated:
a stationary z-up device reads +g, despite gravitational acceleration pointing down.
LinearAccelerationSample excludes gravity. AngularVelocitySample is right-handed
radians/second. Device adapters must validate sensor conventions and synchronization.

## Performance and benchmark hook

Hot math uses primitive doubles, no streams, reflection, boxing, logging, I/O,
caches or mutable global state. Immutable vector/result allocations are deliberate;
CPA/normalization introduce small temporary vectors and Optional results. Profile
before introducing mutable buffers. Squared-distance APIs avoid square roots when
only comparison is needed. StrictMath supplies reproducible transcendental functions.

The test-source MathBenchmark main is a desktop diagnostic hook, outside unit tests:

```powershell
npm run check:core
java -cp "packages/guardian-core/target/test-classes;packages/guardian-core/target/classes" dev.sentinel.guardian.MathBenchmark
```

Use ':' instead of ';' for classpath separation on Unix. The hook warms up, consumes
outputs and reports aggregate timing plus checksum; it is not JMH, a device benchmark
or a latency guarantee. Use repeated forks and a profiler to inspect allocation/GC.
Record device/JVM/build/thermal state and distributions in the experiment log before
making performance decisions. No benchmark numbers have been claimed.

## Task 003 camera geometry

The same module now owns calibrated projection, distortion inversion, explicit
pixel/image transforms, extrinsics, pose, rays and local ground-plane contracts.
Hardware adapters supply calibration and timing; the core performs the geometry.
See [camera model](geometry/CAMERA_MODEL.md), [coordinate frames](geometry/COORDINATE_FRAMES.md),
[image transforms](geometry/IMAGE_TRANSFORMS.md), [ground geometry](geometry/GROUND_GEOMETRY.md)
and [calibration schema](calibration/CALIBRATION_SCHEMA.md). Task 002 math is preserved.

## Task 004 timing and motion

[Time synchronization](motion/TIME_SYNCHRONIZATION.md) and
[IMU mathematics](motion/IMU_MODEL.md) extend the existing contracts without
changing their time, frame, quaternion or specific-force conventions. Stateful
buffers and filters are explicitly single-owner; immutable results remain shareable.
See [motion estimation](motion/MOTION_ESTIMATION.md) for derivative midpoint times,
uncertainty limits and explicit prediction horizons.
