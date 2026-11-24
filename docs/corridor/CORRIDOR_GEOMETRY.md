# Corridor geometry

IMPLEMENTED modes: IMAGE_SPACE_CORRIDOR, GROUND_PLANE_CORRIDOR (camera-coordinate supplied plane), WORLD_SPACE_CORRIDOR (session-local world plane and exact supplied pose). AUTO prefers a supported metric mode, otherwise image fallback. IMAGE explicitly selects the fallback. Fallback reasons are visible; stale/mismatched pose, calibration, image frame, plane or clock cannot yield fresh world geometry.

Metric construction projects the camera origin onto the supplied plane and projects camera forward into that plane. The plane normal must point toward the camera. Forward and right are orthonormal Guardian vectors. Right = forward cross up, consistent with camera right/down/forward axes. The corridor coordinate pair is `(lateral right, forward)`, not a new LOCAL_WORLD axis convention. A parallel forward/normal, invalid quaternion, wrong frame or non-finite input is rejected or falls back.

Four vertices describe the near/far cross sections. Width interpolates linearly; equal widths give a rectangle. `near_m`, `far_m`, half widths, constant expansion and near-boundary band are versioned, finite, bounded research configuration. Defaults (0.5–5 m, 0.45–0.9 m half widths) are PROVISIONAL, not universal body/aid dimensions or stopping margins. No inferred speed, stride or covariance.

Guardian locates a point by dot products with the corridor basis. Forward distance differs from range. Signed boundary distance is Euclidean distance in the plane to the closed four-edge footprint: negative inside, zero on boundary, positive outside (including before near or beyond far). This is a point-footprint relation, not a measured physical object extent.

Image fallback uses a centered lower-image trapezoid, independent of intrinsics/depth/semantics. Its widths are fractions of image width; it makes no metric claim. Original camera image dimensions/frame are explicit even when calibration quality is UNKNOWN. Off-image entity representatives remain UNKNOWN; boxes are not silently clamped into the corridor.

Metric vertices project through Task003 CameraModel, including its distortion policy. Projection rejects invalid/behind-camera/near-zero-Z vertices. A near-plane-crossing polygon is conservatively unavailable rather than extrapolated. Valid off-FOV polygons clip to the image rectangle. Straight edges between distorted vertices are a PROVISIONAL visualization approximation, not exact observed ground area. The geometric polygon and visible image polygon are distinct; `observed_fraction=None` means unmeasured. Unseen volume is always unknown.
