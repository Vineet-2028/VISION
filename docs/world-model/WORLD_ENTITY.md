# WorldEntity

IMPLEMENTED: explicit WorldEntityId(session_id, serial) distinct from TrackId. Current mapping is one-to-one within retained state. Serial numbers never rewind during reset on an existing model. Another TrackId creates a new entity even at identical geometry: false splits are preferred to silent history merges. Reappearance after expiry gets a new world ID. There is no biometric or persistent cross-user identity.

Entity contains category/confidence from tracks, lifecycle, observed/predicted status, latest actual observation time, state time, observation age, image box, optional bearing, depth evidence, candidate camera/world point, position sources/status, image-motion evidence, semantic center-label evidence, history, quality/reasons. Predicted image geometry is inherited from the tracker; no second predictor or smoothing layer is added. Without another tracker update, geometry is held and explicitly marked PREDICTED, not extrapolated or relabeled observed.

Lifecycle: observed tentative tracks are TENTATIVE; other current observed tracks ACTIVE; missing/current predicted observations PREDICTED; tracker LOST or observation age above lost_ns gives LOST. Age above expire_ns removes the entity and increments expired count; EXPIRED is a removal event, not a perpetually retained record. Explicit tracker removals also remove mapped entities.

History is bounded by count and observation-time horizon. Entries contain frame/time, box, category, observation status and uncalibrated track quality. Exact observed depth attaches its value/kind and candidate camera point to the corresponding entry. Prediction history does not copy depth into a new observation. These are compact records, not dense arrays.

PROVISIONAL defaults: 128 entities, 16 history entries per entity, 5-second history, 1-second lost age, 3-second expiry. Existing entities take precedence at capacity; new candidates sort by TrackId and overflow is diagnosed. No geometric re-identification. Tracking fragmentation remains an inherited limitation.
