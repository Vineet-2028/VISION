# Task001–007 integration audit

Date: 2026-10-18. Read-only inspection preceded Task007 edits. This extends the
historical Task001–006 audit; verification results are recorded in TASK007_AUDIT.md.

| Boundary               | Inspection                         | Evidence and limit                                                                                                                                             |
| ---------------------- | ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 001 → 002              | Unchanged architecture             | Root scripts build/test the independent Java core; Spring/web do not import perception runtimes                                                                |
| 002 → 003              | Preserved                          | Guardian core remains authoritative for transforms, quaternions, camera projection and frame units                                                             |
| 003 → 004              | Preserved                          | Capture time, explicit spatial frames, interpolation limits and physical motion remain separate from image tracking                                            |
| 004 → 005              | Rechecked                          | FrameIdentity carries source, sequence, PTS and timing provenance; media and processing clocks remain distinct                                                 |
| 005 → 006              | Rechecked                          | Adapters return original-image DetectionBatch; empty success differs from unavailable/failure; runtime selected by configuration                               |
| 006 → 007              | Implemented/tested                 | Tracker consumes only Sentinel contracts; both real detector caches use the same implementation; raw recovery proposals are distinct from published detections |
| 007 → future consumers | Contract prepared, consumer absent | Immutable TrackSet joins session/frame/time/box keys; predicted state is explicit; no depth, world velocity, risk or Task008 code                              |

Task007's fixed image-space estimator is not a duplicate implementation of physical
TTC/CPA or camera geometry. Pixel velocities include camera motion and are prohibited
as direct physical collision inputs. Bearing metadata remains unavailable; direct
tracking works without calibration. The existing video preprocessing pipeline still
requires its calibration configuration, whose quality may be UNKNOWN.

Single-owner tracker mutation has a thread-identity guard. Snapshot/history values
are immutable and contain no pixels. Tracks, detections, history and assignment are
bounded; removed IDs are emitted only for the current update. Session reset is
explicit, preserves the serial counter, and never joins incompatible timestamps.
Prediction happens on every processed frame, including detector-unscheduled ticks.

Recording schema2 is opt-in with tracking; tracker-disabled records stay schema1.
The existing frame queue, stale-result rejection, decoder limits and component
failure handling remain active. Cleanup finalizes the recorder even if tracker
close fails, covered by a regression.

Replaceability is demonstrated by IoU/motion/two-stage policies and identical
PicoDet/YOLOX downstream inputs. Future appearance or ego-motion changes belong
behind MultiObjectTracker; no vendor tensor or Kalman matrix becomes required API.

No new dependency was added: NumPy was already directly declared and pinned.
Framework-free tracking policy is composed by the lab; web and Spring Boot remain
unchanged. No per-track thread, global tracker, per-frame model/JVM startup, network
telemetry or raw-frame history is introduced. Opt-in JSONL snapshot recording may
be expensive; its cost is measured separately from tracking.

The prepared 300 frames are model-assisted draft links, not reviewed temporal truth.
Task006 reviewed detection labels do not establish Task007 track identity. Consequently
the Task007 quality and Task008 entry gates remain closed pending that review.
