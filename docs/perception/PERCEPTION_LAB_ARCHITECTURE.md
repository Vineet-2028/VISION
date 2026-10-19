# Perception laboratory architecture

## IMPLEMENTED

Dependency: `apps/perception-lab -> guardian-core JAR`. The reverse dependency is
forbidden by the core architecture tests. Spring Boot and Next.js are unchanged.
The pre-task read-only audit checked core frames, timing, calibration, transforms,
synchronization, Java 8 bytecode target, Maven test-only dependencies, application
configuration, root checks, CI and research conventions. No existing mathematical
defect requiring a core rewrite was identified.

The lab has small modules for contracts, strict config, decoder sources, geometry
interop, preprocessing, separate component adapters, scheduler/queue, pipeline,
metrics, recording, optional visualization and CLI. All are owned by one replay
thread. FFmpeg codec threads are explicitly limited to one. No per-frame threads,
executors, global mutable frame store, service container or event bus exists.

`FrameSource` is an iterator of immutable buffer-owning `Frame` or typed `SourceIssue`;
iterator exhaustion is EOS. VIDEO_FILE is implemented; synthetic sources are test
adapters. IMAGE_SEQUENCE, LIVE_CAMERA and RECORDED_SESSION are conceptual reserved
types and are rejected by current operational configuration.

Offline replay pulls only when the consumer is ready. Realtime file replay maps
the first selected PTS to a process-clock playback anchor, then admits due frames
to a bounded DROP_OLDEST or LATEST_FRAME queue. It has one future-frame lookahead.
It checks freshness before processing. This mapping is playback pacing, not evidence
of camera/sensor clock synchronization. All callbacks execute synchronously; callers
must not retain frame buffers or perform blocking work there.

Schemas reject unknown fields, duplicate keys, nonfinite values, missing geometry,
unknown distortion models and invalid quality evidence. Core constructors validate
distortion invertibility and extrinsics. Source dimensions must match calibration
unless `source_scaling` explicitly declares a pure resize. Arbitrary source crops,
warps, EIS and rotations are not inferred. Supply matching effective calibration.

Headless execution never imports Tk. Optional Tk viewer uses FrameInfoOverlay and
shows the source frame, identity, timestamp, calibration status, mode and measured
rates/latency. Its rendering copy/cost is optional and separately measured. Geometry
inspection uses the Java camera model. Unknown quality means nominal geometry,
never a safety guarantee. Native DLL/JAR startup is a session cost, not per-frame work.

## PLANNED

Typed outputs are deliberately minimal extension contracts. Real detector/depth/mask/
flow tensors, source adapters, normalization policies, accelerated arrays, adaptive
scheduling, temporal joins, pause/step controls and mobile implementations need
their own tests and design. No risk/attention algorithms or warning speech exist.

## RESEARCH

See RND-LAB-001..012. Desktop/JVM parity does not validate camera calibration,
physical exposure timestamps, sensor alignment, inference quality or mobile budgets.
