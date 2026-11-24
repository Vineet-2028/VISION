# WorldState schema 1

Task012 additive extension: optional `image_geometry` independently identifies the original camera image dimensions and evidence; optional `ground_plane` is a supplied frame/time-bound assumption, not inferred ground truth. `WorldSurfaceState.samples` contains at most 768 `(x, y, flags)` point samples, not a dense mask or exact area representation. Old producers may omit these fields; new consumers expose missing/fallback status. No existing field changes units or meaning.

IMPLEMENTED fields: session_id, state_timestamp (source-clock nanoseconds), camera_state, entities (tuple), surface_state, scene_quality, source_ages, subsystem_status, capabilities, provenance, diagnostics, schema_version=1. All nested published structures are frozen dataclasses, tuples, primitive values, immutable existing contracts, or compact region boxes. No mutable model maps, filter matrices, images, dense flow, logits or masks escape.

EvidenceSource retains subsystem, FrameIdentity, age_ns, freshness/status, original observation status, source quality, validation status, bounded provenance tuple and optional public reason code. Source age is state_timestamp minus observation_ns, never processing-clock minus media PTS. Failure metadata is distinct from retained payload evidence: a failure at t1 cannot relabel a payload from t0.

Camera state preserves exact supplied DEVICE-to-LOCAL_WORLD pose, calibration hash/quality, camera-motion frame pair, rotation, translation direction and scale status. LOCAL_WORLD is session-local and drift-unvalidated. No pose is integrated from visual ego motion. IMU availability remains UNAVAILABLE unless a future explicit adapter supplies it.

Recording schema 6 adds world_state; nested WorldState has independent schema 1. Old recording variants remain supported when world model is disabled. JSON is only produced by the opt-in recorder or offline measurement tools. Unknown schema versions must be rejected by future readers, never silently reinterpreted.

PLANNED mobile representation: Java/Kotlin immutable records/data classes, enums, signed 64-bit source timestamps, explicit optional estimates, bounded arrays. No Python object identity is a semantic identifier.

Task012 contract: camera_state, entities.image_geometry/position_camera/position_world, surface_state, capabilities and per-field evidence. Task013: bounded history, timestamps and source-supported point estimates; prediction remains external. Task015: observation_status, freshness, quality, validation and capabilities; no inference of certainty merely from non-null positions. Future attention may use WorldEntityId; no attention policy is present.
