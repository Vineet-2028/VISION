# Orientation propagation

## IMPLEMENTED

Quaternion is Hamilton (w,x,y,z), active right-handed rotation. q maps DEVICE into
LOCAL_WORLD. For body-frame angular velocity omega held constant over dt:

    theta = norm(omega)*dt
    delta_q = [cos(theta/2), omega/norm(omega)*sin(theta/2)]
    q_next = q * delta_q

Right multiplication is essential for a BODY rate. World-frame rates would require
a different composition; ImuMath.propagate accepts only DEVICE rates. Rate timestamp
equals the starting orientation timestamp. Caller supplies maximum integration gap.
Zero dt preserves the original estimate. Quaternion construction normalizes each
result; no bias/noise/drift correction is hidden.

SLERP takes the shortest quaternion path. If dot(q0,q1)<0, the second representation
is negated. Clamp roundoff in the dot product; use normalized linear interpolation
when dot>0.9995, otherwise sine-weighted spherical interpolation. Antipodal
representations describe the same rotation and do not cause a long-path spin.

Orientation and pose confidence are scores, not calibrated probabilities. Propagation
retains the supplied confidence as an upper bound but clears derived angular deviation
because process noise has not been characterized. This is nominal extrapolation,
explicitly separate from interpolation and bounded by caller horizon.

Tests cover known yaw/pitch/roll, noncommuting initial orientation/body rate, tiny
increments, zero rate, antipodal SLERP and seeded normalization invariants.

## PLANNED / RESEARCH

Gyro integration drifts without bias correction and absolute/external observations.
V1 expects a validated adapter-supplied orientation estimate. Complementary filtering
and ESKF remain research, not implemented orientation stabilization.
See [Solà's quaternion/ESKF reference](https://arxiv.org/abs/1711.02508) for the
distinction between nominal orientation and orientation error.
