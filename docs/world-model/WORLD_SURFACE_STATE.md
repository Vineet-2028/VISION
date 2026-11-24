# WorldSurfaceState

IMPLEMENTED: source EvidenceSource, validation_status=UNVERIFIED, camera image identity/dimensions, bounded original SurfaceRegion metadata, flag pixel counts, optional exact-source semantic class counts, geometry_status. Region identity is local to its source frame; it is not a persistent world object ID.

All Task010 draft semantics remain UNVERIFIED, including propagated or stale outputs and derived surface counts. Freshness does not imply ground-truth validity. SurfaceRegion carries semantic class, pixel area, original-image box and bottom-connected flag. Frame-level evidence carries provenance/age/status for every region. Counts are supporting image-space evidence, not measured navigability.

World model retains no dense semantic or surface masks. It computes compact summaries once per accepted event and keeps only the latest bounded surface payload. Optional per-entity center labels use exact-frame Guardian mapping and do not overwrite categories. Disagreement is a public diagnostic, not a decision that either model is correct.

After semantic freshness expires, retained evidence becomes STALE. Propagated observation status is preserved separately even when stale. Retention expiry discards regions; repeated failure ticks cannot extend payload lifetime. Missing semantics produces a valid unavailable surface state.

GROUND_PLANE_UNAVAILABLE is explicit. No ground plane, camera height or global localization is assumed from pixels. IMPLEMENTED optional project_surface_pixel requires a same-frame supplied pose, explicit plane point/normal and provenance, current surface source and pixel inside the referenced region box. Guardian computes a nominal ray/plane candidate, tagged GROUND_PLANE_PROJECTED and UNVERIFIED. One candidate per region is retained, bounded by region count. Box inclusion does not prove a pixel belongs to the exact semantic component or physically touches ground. This is a supplied-assumption diagnostic, not 3D reconstruction or Task012 corridor logic. Richer projected polygons remain PLANNED.
