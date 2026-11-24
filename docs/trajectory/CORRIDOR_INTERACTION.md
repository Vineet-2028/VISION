# Frozen corridor geometry

IMPLEMENTED: raw image trajectories compare bottom-center paths against the current Task012 image polygon. Convex segment clipping finds entry even when a path enters and leaves between sample horizons. Successive samples define a piecewise-linear path, so alternate predictors are not assumed to move directly from origin to their final sample. This is exact for the implemented CP/CV path; unknown curvature between samples is not reconstructed. Outputs retain current predicted relation, per-horizon relations and predicted_corridor_entry_time_ns. An entity already inside has entry 0; no entry is null.

This is point-path geometry against a frozen camera corridor, NOT time to collision, footprint overlap, safe navigation or an alert. Outside entities are retained. No user velocity is assumed. Bearing, stabilized residual and world-research trajectories currently return UNKNOWN corridor mapping, while their independent trajectories remain available. Metric interaction mapping belongs behind a future explicit coordinate adapter; no radians/meters are projected into pixel geometry by assumption.

Synthetic crossing, parallel outside, departure, stationary and edge-contact fixtures cover the image implementation. Polygon is the convex Task012 contract; alternate analyzers must preserve that invariant.
