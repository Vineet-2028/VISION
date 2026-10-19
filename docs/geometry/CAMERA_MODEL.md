# Calibrated camera model

Task 003 extends the independent Java 8 guardian-core library. No camera driver,
image processing, network, serialization or ML dependency enters this module.
Inputs are immutable snapshots; computations have no I/O, hidden caches or clocks.
Task 002 vector, quaternion, transform and normalized detection contracts remain.

## Coordinates and equations

All angles are radians. CAMERA is right-handed: x right, y down, z optical forward.
PixelPoint uses continuous IMAGE edge coordinates; CameraPlanePoint is dimensionless
and unbounded; NormalizedImagePoint is a distinct [0,1] image fraction.

| Equation                                                                                              | Implementation                       | Assumptions and reference tests                                                                                                           |
| ----------------------------------------------------------------------------------------------------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| x=X/Z, y=Y/Z; u=fx*x+cx, v=fy*y+cy                                                                    | CameraModel.cameraPointToPixel       | Z > configurable near plane; CameraGeometryTest checks axes, near/behind, off-image, non-square focal lengths                             |
| xd=(u-cx)/fx, yd=(v-cy)/fy; r=normalize([undistort(xd,yd),1])                                         | CameraModel.pixelToCameraRay         | Matching calibration ID, image identity and dimensions; principal point gives (0,0,1), (1500,500) with f=1000,c=500 gives (1,0,1)/sqrt(2) |
| azimuth=atan2(x,z), elevation=atan2(-y,hypot(x,z))                                                    | DirectionAngles, CameraModel.bearing | Azimuth (-pi,pi], elevation [-pi/2,pi/2]; poles reject undefined azimuth; analytical pi/4 and distorted bearing tests                     |
| left=atan2(-cx,fx), right=atan2(W-cx,fx); top=atan2(cy,fy), bottom=atan2(cy-H,fy)                     | CameraIntrinsics angle helpers       | Ideal undistorted limits; asymmetric and off-center tests                                                                                 |
| FOVx=right-left, FOVy=top-bottom                                                                      | CameraIntrinsics                     | Not distorted sensor FOV; centered case reduces to 2*atan(W/(2*fx))                                                                       |
| normalized angle = modulo 2*pi in (-pi,pi]; difference=normalize(normalize(target)-normalize(source)) | Angles                               | Finite radians; huge values, branch boundaries, multiple turns tested                                                                     |

Intrinsics require finite positive fx/fy and positive dimensions, but principal
points may lie outside the image after calibration/crop. Zero skew is the explicit
V1 approximation commonly appropriate to mobile cameras; it is not assumed true
for every device. Import through withSkew rejects any nonzero skew. Never discard
an actual measured skew value. UNKNOWN/DEGRADED calibration can produce nominal
geometry, not a safety assurance; INVALID returns unavailable. VALID requires
reported RMS and sample count, but no arbitrary accuracy threshold is embedded.

ProjectionResult separates an available finite mathematical pixel from insideImage.
Visibility is half-open [0,W) x [0,H), excludes occlusion and has no far plane.
CameraFrustum is only this minimal test. Public invalid inputs/frame mismatches
throw; numerical non-representability and unavailable geometry return empty results
where the method has an optional result. Scalar/vector operations can explicitly
throw on overflow. NaN and infinity are never successful outputs.

## Distortion and inversion

LensDistortionModel permits future families without silently approximating them.
NoDistortion is an explicit choice, never an automatic fallback. Brown-Conrady uses
dimensionless ideal camera-plane coordinates and coefficients k1,k2,k3,p1,p2:

```text
r2 = x*x + y*y
R = 1 + k1*r2 + k2*r2*r2 + k3*r2*r2*r2
xd = x*R + 2*p1*x*y + p2*(r2 + 2*x*x)
yd = y*R + p1*(r2 + 2*y*y) + 2*p2*x*y
```

The calibrated maxRadius disk is mandatory. The constructor requires the conservative
Jacobian lower bound below to exceed 1e-12; some invertible models are deliberately
rejected rather than accepting ambiguous inverse branches:

```text
1 + min(0,k1)*3*Rmax^2 + min(0,k2)*5*Rmax^4
  + min(0,k3)*7*Rmax^6 - 8*Rmax*(abs(p1)+abs(p2))
```

Each radial term has eigenvalues k*r^(2j) and (2j+1)*k*r^(2j).
The tangential Jacobian's absolute row sums are bounded by 8*Rmax*(|p1|+|p2|).
A positive bound makes the symmetric Jacobian positive definite throughout the
convex disk and the map injective there. This is a numerical domain certificate,
not evidence that the lens model fits a real camera.

Inversion uses the analytic 2x2 Jacobian and damped Newton steps. Start at the
distorted coordinate, bounded to the calibrated disk; each step tries at most 12
halvings and must reduce residual within the disk. Singular/nonfinite arithmetic,
exhausted iterations, unavailable domain or failure to improve returns empty.
Defaults: 30 steps, normalized-plane residual tolerance 1e-10; max steps configurable
from 1 to 1000. Near-plane default is 1e-6 meters, parallel tolerance 1e-12.
These are mathematical guards, not physical measurement uncertainties.

DistortionTest checks hand-calculated radial and tangential values, zero/strong
distortion, grid roundtrips (1e-8 recovery tolerance), domain rejection and forced
non-convergence. CameraGeometryTest covers projection/ray roundtrips and finite
failure at extreme focal lengths. See test assertions for each numerical tolerance.

## Limits and performance

AngularExtent is a four-corner bearing approximation, not guaranteed extrema along
nonlinearly distorted edges. Detection bearing uses center; ground contact uses
bottom-center and is only a candidate. No metric size or distance is inferred.
The tempting f*physicalSize/pixelSize estimates optical-axis depth only under a
front-parallel known-size model. Pose, truncation, class variability, boxes and
camera angle violate it. A future estimator must return uncertainty and provenance;
there is intentionally no distance-estimator API yet.

Hot paths use doubles and bounded loops, no streams/reflection/matrices/caches.
Small immutable points, vectors, optionals and results allocate; corner extents
perform four inversions. Callers should reuse rays for repeated queries on identical
pixels and calibration. Profile before lookup maps, distortion grids, vectorization
or SIMD. GeometryBenchmark is an opt-in desktop diagnostic, not a device latency test:

```powershell
npm run check:core
java -cp "packages/guardian-core/target/test-classes;packages/guardian-core/target/classes" dev.sentinel.guardian.GeometryBenchmark
```

The [OpenCV calibration reference](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html)
provides the pinhole and coefficient conventions; OpenCV is not a runtime dependency.
