# Surface and free-space evidence

IMPLEMENTED: world fusion samples at most a 32x24 regular lattice of original-image SurfaceFlag values. This is a bounded point sample, not an occupancy grid, dense mask copy, exact area statistic or ground map. At most 768 primitive triples are retained; dense semantic masks remain outside WorldState.

The analyzer intersects those samples with the current visible corridor polygon using vectorized constant-edge operations. It requires matching image/frame/clock and exact source-frame alignment: an older mask is not assumed aligned after camera movement. Missing, propagated-without-established-registration, failed, stale, mismatched or absent surface evidence yields UNAVAILABLE coverage, null candidate fractions and unknown fraction 1.

CorridorSurfaceEvidence reports candidate-ground, candidate-traversable, obstacle and unknown fractions of the selected samples. Flags may overlap: these are not probabilities or necessarily disjoint area partitions. Potential traversable counts exclude unknown/obstacle/occupied flags. Unknown includes unknown bits and samples with no supported ground/obstacle evidence. Every result retains UNVERIFIED status, source age and provenance. Small or unsampled obstacles can be missed; no sampling accuracy qualification is claimed.

FreeSpaceEvidence reports UNKNOWN, optionally AVAILABLE_EVIDENCE and OCCUPIED_EVIDENCE. Inside/intersecting entity IDs and semantic obstacle samples are occupancy evidence only. Ground evidence does not mean free or walkable. Unseen/occluded physical space remains UNKNOWN even when every visible sample has a label. `unknown_fraction` refers only to sampled image evidence, never the entire physical corridor.

No occupancy grid, SLAM, depth-discontinuity detector, route planner or warning system was added. These were not needed to establish the bounded current-state contract. Detailed occlusion geometry and exact coverage are UNVALIDATED/PLANNED; absence of detection is never converted into empty space.
