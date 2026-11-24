# Task012 corridor architecture

IMPLEMENTED: `CorridorAnalyzer.analyze(WorldState) -> CorridorAnalysis` is a stateless, synchronous replacement boundary. The pipeline runs it immediately after the world model. It does not poll detectors, alter WorldState, remove outside entities, read a hidden clock, retain histories, or queue snapshots. Realtime retains the existing latest-frame bounded queue; offline replay processes all admitted states.

`UserCorridorState` (also named `UserCorridor`) contains an `InteractionZone`, explicit source timestamp, mode/frame, compact polygon, optional metric basis/dimensions, heading/ground evidence, quality and reasons. `CorridorAnalysis` adds entity relations, sampled surface evidence, free-space evidence, schema/version and provenance. No output is a route, collision decision, hazard label or instruction to walk.

The hybrid implementation owns evidence selection and image heuristics. Guardian's Java 8-compatible `CorridorGeometry` owns metric vectors, plane projection, bases, point coordinates and signed footprint distance. Existing Task003 camera distortion/projection and transforms remain authoritative. The process-scoped JVM is reused; no per-update JVM startup.

Two additive WorldState schema1 fields resolve genuine integration gaps: `image_geometry` (independent of segmentation) and `ground_plane` (an explicitly supplied assumption). `WorldSurfaceState.samples` carries at most 768 regular image point samples. Old producers can omit these fields: missing image geometry produces an explicit UNAVAILABLE corridor; missing plane produces image fallback. Unknown WorldState schema versions are rejected.

The prototype world model supplies image metadata and compact surface samples. It does not infer or invent a ground plane from semantic labels. A synchronized alternative WorldModel/pose adapter can supply `SuppliedGroundPlane`; real footage currently has no physical calibration/pose/plane. Camera-forward is a gaze/device proxy, not validated body direction or walking intention. Standing still, looking sideways and turning the head remain ambiguous.

PLANNED: body/walking heading may replace the implementation behind the same output contract and heading metadata. Personalization changes versioned widths/lookahead, not geometry algorithms. Speed-adaptive lookahead requires a validated speed signal. Task013 has not started.

USER_CORRIDOR != SAFE_PATH. INSIDE != HAZARD. OUTSIDE != SAFE. FREE_SPACE_EVIDENCE != GUARANTEED_FREE_SPACE.
