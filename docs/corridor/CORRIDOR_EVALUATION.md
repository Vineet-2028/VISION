# Evaluation scope

IMPLEMENTED tests cover analytical rectangles/tapers, rotated plane-aligned corridors, inside/boundary/outside/behind/far relations, image projection/clipping, source frame/time validation, calibration/depth/semantic absence, unknown samples, unverified semantics, immutable outputs, bounded counts, alternative producers/analyzers and recording integration.

MEASURED results are recorded in `docs/research/results/task012-corridor-2026-10-22.md` and its JSON companion. Separate compute latency from world-update intervals and total replay wall time. RSS includes Python/JVM/model allocations, not just the analyzer. Quantiles use a bounded recent window (up to 2048); counts/min/max/mean cover the run. Synthetic stress reuses immutable snapshots to isolate compute and does not validate perception accuracy.

The real replay uses existing permitted local Sentinel screen-recorded footage and existing adapters. It cannot establish camera calibration, physical motion or ground-truth walkability. Campus, sidewalk, road-edge, crowd, parked-obstacle, turns, high-camera-motion and mixed-scene strata require reviewed scenario labels and independent recordings before any per-scenario accuracy claim. Do not invent those labels from this single correlated recording.

UNVALIDATED: safe path, free-space safety, physical positioning, semantic truth, body heading and production safety. PROVISIONAL: camera-forward trapezoid, research widths/boundary margins and sample density. PLANNED: larger independent scenario coverage, body heading, exact region/occlusion geometry and hardware-specific qualification. Task013 is not implemented here.
