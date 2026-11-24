# Surface evidence

IMPLEMENTED: separate immutable `SurfaceEvidenceFrame` with original-camera uint8 flags, source/session identity, observation status, semantic and optional object provenance, bounded region metadata and diagnostics.

Flags: UNKNOWN, GROUND_CANDIDATE, POTENTIAL_TRAVERSABLE, OBSTACLE_EVIDENCE, OCCUPIED_REGION and BOUNDARY. Overlapping flags express independent evidence, not an exclusive safety class. Road is ground-candidate evidence, never universally safe or universally forbidden. Stairs and curbs retain semantic identity and obstacle/change evidence; neither becomes generic traversable ground. Unknown pixels never become potential-traversable evidence.

SIDEWALK/FLOOR/PATH provide potential-traversable semantic evidence. GRASS/GROUND_OTHER retain uncertainty. Occupancy from exact-frame generic detections or observed tracks is a separate overlay; it does not erase or relabel the original semantic mask. Boxes larger than the configurable fraction (default 25%) are ignored with a diagnostic; at most 512 boxes are considered. This rectangle heuristic may overstate occupancy and is not complete obstacle detection.

Connected components preserve disconnected islands and report bottom contact. Default maximum 128 regions (configurable up to 256); bounding boxes use continuous camera edges. Exact boundaries stay in the mask; no unbounded polygon list is retained. Small-component thresholds filter metadata only. Morphological filling/closing is deliberately deferred: it could destroy narrow paths or fill unknown holes.

Depth consistency is an optional exact-frame, exact-native-grid API. It reports a dimensionless neighbor-discontinuity diagnostic and depth provenance. It does not report curb height, slope, drop depth or safety. Mismatched grids explicitly return unavailable; mismatched frames reject. Ground-plane projection is deferred until calibrated geometry is available.
