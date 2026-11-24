# Task010 adversarial audit

Scope: Task001-009 integration and Task010 local semantic evidence. Task011 is not started.

## Pre-task read-only inspection

Inspected prior integration/audit reports, FrameIdentity, detection, tracks, depth, flow/ego, Guardian ImageMapping, scheduler, recording, dataset manifests, dependency lock and BOM before integration edits. Source observation times remain authoritative; semantic frames can bind independently. Prior components do not expose safe-path decisions. Existing no-op segmentation was a placeholder and has been replaced by an optional contract. `npm run verify` baseline exited 0 (480 tests); the existing five reviewed development advisory entries remain.

## Findings and corrections

| Severity         | Files                                | Finding / consequence                                                                                 | Resolution                                                                                       |
| ---------------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| CRITICAL         | semantic_runtime.py                  | Composing two resize mappings with the same destination identity was rejected by Guardian             | Compose the mathematically equivalent direct output-grid scale; real inference exercises it      |
| CRITICAL guarded | semantics.py, semantic_evaluation.py | Wrong class IDs, frame joins or draft truth could fabricate evidence                                  | Versioned IDs, immutable masks, exact identity validation, draft/ignore gates                    |
| HIGH             | pipeline.py                          | Late asynchronous output could contribute outdated ground evidence                                    | Preserve source identity; expire to STALE; no current-frame object fusion                        |
| HIGH guarded     | semantic_worker.py                   | Slow segmentation could create backlog or stall every frame                                           | One in-flight job, skip busy ticks, explicit shutdown; offline synchronous mode remains separate |
| HIGH             | semantic_evaluation.py               | Missing predicted boundary could return an undefined score despite reference boundary                 | Zero boundary F1 when an existing boundary is missed                                             |
| HIGH guarded     | recording.py                         | Generic serialization of semantic arrays would duplicate dense maps                                   | Schema 5 compact summaries; dense arrays excluded before dataclass conversion                    |
| MEDIUM open      | checkpoints / data                   | Cityscapes lineage and separate weight grants are not product-cleared; reviewed semantic truth absent | Research-only comparison, no redistribution or product approval; human review required           |
| MEDIUM open      | semantic_worker.py                   | Native job shutdown waits; CPU contention and real-time rates remain unqualified                      | One native thread default; measure before production use                                         |
| LOW open         | surfaces.py                          | Region metadata uses bounded boxes plus exact raster boundary, not simplified polygons                | Document representation; add polygons only when a consumer requires them                         |

No raw footage upload, telemetry, identity inference, cloud runtime, navigation or safety output. No auto training. Runtime masks/history are bounded. The annotation packet is finite offline tooling, not an inference cache. Final verification and measurement status belong in the Task010 report; pending results must not be read as passes.
