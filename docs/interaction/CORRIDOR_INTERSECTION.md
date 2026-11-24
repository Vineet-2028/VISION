# Temporal corridor geometry

IMPLEMENTED: bounded piecewise-linear segments between the supplied origin and Task013 samples. Convex clipping yields entry/exit intervals, including intersections entirely between sampled horizons. No sample or segment extends beyond the configured horizon or final supplied sample. Continuous geometric entry is a model prediction, not an observed event.

Image geometry uses the matching raw camera frame. Stabilized-image predictions cannot silently map to a raw corridor. Metric research trajectories can map to a matching world corridor's orthonormal lateral/forward plane. This is ground-plane projected separation, not three-dimensional clearance. Bearing has no supplied polygon mapping and reports UNKNOWN corridor geometry.

Nominal point intersection takes priority over POSSIBLE_INTERSECTION. A segment whose minimum polygon distance is within the maximum of adjacent envelope radii may intersect: this is a conservative swept-disk bound, not a probability or an exact variable-radius timing window. The first segment uses the first supplied radius as an upper bound. UNKNOWN envelope representations cannot establish a miss. Earliest/latest possible entry remain unavailable because the contract does not justify exact timing precision.

CROSS_CORRIDOR requires entry/exit and opposite lateral bounding sides. Returning through the same side is PREDICTED_ENTER_EXIT. Other neutral types include REMAIN_INSIDE, PREDICTED_EXIT, PREDICTED_ENTER, PASS_NEAR and REMAIN_OUTSIDE. Boundary contact counts as intersection. Exit at the final horizon is unresolved rather than extrapolated. Intervals preserve later re-entry. No interaction label means collision, risk or safety.

Closest corridor approach is the minimum unsigned distance to the region over all bounded segments, with the earliest minimizing horizon. It is distinct from object-reference CPA. Pixels stay pixels; world projection meters retain research validity. The entity's full physical extent and future camera/user motion are not known.
