# Image transformations

ImageTransform stores an invertible six-scalar affine map plus source/destination
image identities and dimensions. It supports scale, crop, pad, clockwise quarter
turns, continuous letterbox, composition and exact algebraic inverse. Arithmetic
overflow rejects the result. No general projective or stabilization warp is implied.

| Operation        | Coordinates / intrinsics                                 |
| ---------------- | -------------------------------------------------------- |
| Pure scale       | u'=sx*u, v'=sy*v; fx',cx'=sx*(fx,cx), fy',cy'=sy*(fy,cy) |
| Crop at left,top | u'=u-left, v'=v-top; cx'=cx-left, cy'=cy-top             |
| Pad at left,top  | u'=u+left, v'=v+top                                      |
| 0 degrees        | (u,v), dimensions (W,H)                                  |
| 90 clockwise     | (H-v,u), dimensions (H,W)                                |
| 180 clockwise    | (W-u,H-v), dimensions (W,H)                              |
| 270 clockwise    | (v,W-u), dimensions (H,W)                                |
| Letterbox        | s=min(Wnew/W,Hnew/H), pad=((Wnew-s*W)/2,(Hnew-s*H)/2)    |

Coordinates are continuous pixel edges, not integer array indices. Thus rotation
uses W-u, never W-1-u. The first center (0.5,0.5) maps to the corresponding center.
Crop/pad bounds use wide integer arithmetic and require the region to fit.
Geometry-changing operations need new IMAGE identities, even at the same resolution.
All public transform factories require a distinct destination identity, including
zero-turn or same-size operations. Inverse/composition may return to the original
identity; their intermediate frame and dimensions are checked.

CameraIntrinsics.scaledTo is only for known pure scaling; croppedTo is an explicit
crop. Both return intrinsics, not an implicitly reusable calibration version.
RotatedIntrinsics returns rotated K, image map and original-camera-to-rotated-camera
Rz transform with a distinct CAMERA identity. Odd turns swap focal lengths;
principal point follows the table. Do not reuse tangential distortion coefficients
in this rotated basis. Prefer mapping rotated/model pixels back to the original
camera image and using its original calibrated lens model.

The ideal letterbox helper uses fractional symmetric padding. Real preprocessors
often round resize dimensions and split odd padding asymmetrically. Their adapter
must compose the actual integer-sized scale and explicit pad operations instead.
Never infer the inverse from aspect ratio alone when actual preprocessing is known.

Future detector adapter sequence:

1. Preserve exact original->model ImageTransform and calibration capture metadata.
2. Convert model output boxes to model pixels, without silently clamping.
3. Apply transform.inverse() to restore original pixels.
4. Explicitly clamp only if the consuming contract requires it.
5. Use the original calibration and capture metadata for rays/bearings.

PixelBox permits off-image and zero-area raw boxes, rejects inversions and nonfinite
coordinates, and maps all four corners. BoundingBox2D retains Task 002's bounded
[0,1], positive-area invariant. Conversion to it rejects out-of-bounds or empty
boxes; clamp can produce empty boxes which must be filtered explicitly. Bounds
may touch W/H although point visibility uses the half-open image domain.

ImageGeometryTest checks hand-computed scale/crop, all rotations and optical basis,
odd padding, tall/wide/square letterbox, inverse point/box roundtrips and integer
dimension extremes. An affine inverse restores coordinates, not lost crop pixels.
