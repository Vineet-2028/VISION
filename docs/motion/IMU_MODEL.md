# IMU measurement model

## IMPLEMENTED

DEVICE is right-handed x right, y body-forward, z up. LOCAL_WORLD is session-fixed
with z gravity-up. Gyro is body angular velocity in radians/second. Specific force
is f=a-g, in m/s². Raw ImuSample retains its Task 002 meaning; SpecificForceSample
supports asynchronous DEVICE accelerometer observations. LinearAccelerationSample
always excludes gravity.

GravityModel supplies g_world=(0,0,-g), with configurable positive magnitude.
9.80665 m/s² is a nominal reference, not measured local gravity. For an aligned
DEVICE->WORLD rotation R:

    f_world = R*f_device
    a_world = f_world + g_world

At rest, a=0, so f=-g=(0,0,+g) in world and compensation returns zero.
The stationary, inverted, quarter-turn and known upward-acceleration tests establish
the sign independently of roundtrip tests. Translation never acts on acceleration.
Orientation must be evaluated at the specific-force measurement timestamp and clock.

GyroscopeBiasEstimate and AccelerometerBiasEstimate wrap existing typed uncertainty
contracts. Correction subtracts bias in the matching DEVICE frame. Bias must be known,
not from the future, and within the caller's maximum age; otherwise correction is
unavailable. Bias learning is not implemented. Returned nominal samples do not claim
propagated uncertainty: callers retain original sample, bias and orientation evidence.

StationaryDetector evaluates a supplied ordered window using configured sample count,
span, maximum gaps, angular-rate magnitude, force-magnitude distance from gravity
and force-magnitude variance. It returns STATIONARY_CANDIDATE, MOVING or
INSUFFICIENT_DATA. Every force magnitude must satisfy the configured gravity band.
This cannot distinguish stationary from constant translational velocity, and some
dynamic accelerations can mimic gravity. It is never a safety classifier or proof
that a zero-velocity update is justified.

## PLANNED / RESEARCH

Characterize gyro white noise and bias, accelerometer noise/bias, axis misalignment,
scale errors, temperature effects and saturation. Stationary calibration needs a
verified stationary condition and known orientation/gravity assumptions; a candidate
window alone cannot uniquely separate all biases from gravity. No sensor noise,
accuracy or stationary thresholds have been measured. See RND-IMU-001..012.
