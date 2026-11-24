# World model architecture

IMPLEMENTED: optional local single-writer `PrototypeWorldModel` consumes Sentinel contracts and publishes immutable `WorldState` schema 1. `WorldModel` is the replaceable pipeline-facing protocol: consume(FrameResult), snapshot(timestamp), reset(session_id, source_id), close(). Task012 and later consumers must depend on WorldState, not private maps.

Perception owns observations. World model owns bounded derived state, source ages and conservative evidence associations. Providers do not depend on this layer. No detector, tracker implementation, neural runtime, OpenCV flow operation or vendor tensor is imported by world-model modules. Guardian remains the geometry authority; no per-update JVM startup occurs.

FrameResult optionally contains world_state. Existing configurations remain disabled unless world_model is configured. Publication is frame/update-driven, independent of individual model cadences. No extra thread or queue is created. Pipeline remains single-use and closes the model on completion/failure. Immutable snapshots may be retained by downstream consumers, whose retention is their responsibility.

The world model introduces no risk, trajectory, TTC/CPA decision, warning, navigation, identity recognition, cloud service or physical velocity. Task012 now derives corridor evidence through the separate WorldState consumer described in `docs/corridor/USER_CORRIDOR_ARCHITECTURE.md`; it does not add safety decisions to world fusion.

PROVISIONAL: exact-only object-depth association and conservative identity splitting. UNVALIDATED: physical accuracy, semantic ground truth, production safety. Optional exact-time supplied-ground projection delegates to Guardian. Without calibrated pose/plane assumptions it is unavailable; no plane is inferred from segmentation.
