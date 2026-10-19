# Rays, planes and local ground

Plane3D stores point q and unit normal n in the same spatial frame. Signed distance
is n dot (p-q); projection is p-n*distance. For ray origin o and unit direction d:

```text
t = -n dot (o-q) / (n dot d)
intersection = o + t*d
```

Plane3D.rayIntersection rejects frame mismatch and returns unavailable when the
denominator is within configured parallel tolerance, t<0 or arithmetic is nonfinite.
Origin-on-plane with a nonparallel ray gives t=0. A coplanar parallel ray has no
unique intersection. SpatialGeometryTest covers these analytical cases and tilted
ground; this is a ray, not an infinite line.

GroundPlaneEstimate is an optional LOCAL_WORLD plane, monotonic time, confidence,
optional normal/offset deviations and source. It is a local approximation, never
a claim that stairs, slopes or all visible objects lie on one plane. Unknown/invalid
ground is represented by an absent plane, zero confidence and absent deviations.
No plane estimation or confidence threshold is implemented.

SpatialGeometry.groundIntersection checks world identity and exact capture-time
alignment. GroundIntersectionCandidate carries a nominal point, original ground
estimate and ray. It is NOT a precise measured location and contains no propagated
covariance. Callers must also retain the calibration, extrinsics and pose provenance.
Detection bottom-center is a groundContactRayCandidate only: occlusion, truncation,
box error, raised objects, non-ground objects and perspective can invalidate contact.

## Uncertainty requirements for later work

Pixel localization uncertainty, intrinsic parameter covariance, distortion fit,
extrinsic translation/rotation uncertainty, time-aligned pose uncertainty and ground
normal/offset uncertainty all affect the world ray and intersection. Near the horizon,
small angular errors can create very large position errors. Missing uncertainty
means unknown, not zero. Task 004+ must define covariance/provenance contracts,
propagate Jacobians or evaluate Monte Carlo samples, validate calibration against
holdouts and reject ill-conditioned estimates using evidence-based criteria. Current
confidence scores are not probabilities and nominal coordinates cannot justify
steering or safety decisions.

## Horizon: derived, implementation deferred

Given time-aligned ground normal in world and calibrated camera-to-world rotation,
rotate the normal into CAMERA: n=R_worldToCamera*n_world. In ideal undistorted pixels:

```text
(nx/fx)*u + (ny/fy)*v + nz - nx*cx/fx - ny*cy/fy = 0
```

Translation does not affect the horizon. If nx=ny=0, there is no finite image line.
Lens distortion generally maps this line to a curve. A future API needs a line/curve
representation, domain clipping/sampling, distortion failure handling and orientation
uncertainty. No line API is added until a consumer requires it; orientation is supplied,
never estimated here.

## Planar homography research

Choose ground origin O and orthonormal plane basis e1,e2. Let C be camera center in
world and R rotate world to camera. With ideal intrinsic matrix K:

```text
H = K * [R*e1, R*e2, R*(O-C)]
pixel_homogeneous ~ H * [s,t,1]
```

This maps only points on the assumed plane. Distorted pixels must first be
undistorted. Inversion is ill-conditioned near the horizon and degenerates when
the camera lies in the plane. The existing ray-plane path supplies the needed
mapping without a general matrix dependency; no Matrix3 API is justified yet.
The [OpenCV homography tutorial](https://docs.opencv.org/4.13.0/d9/dab/tutorial_homography.html)
provides the planar projective relationship; this is research, not a runtime dependency.
