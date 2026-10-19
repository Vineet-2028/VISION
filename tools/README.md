# Tools

Task008 adds `download_depth.py` for explicit pinned model acquisition,
`depth_benchmark.py` for bounded local comparisons and opt-in diagnostic maps, and
`depth_parity.py` for a fixed-shape ONNX experiment. These are covered by lab linting.
See [depth runtime](../docs/depth/DEPTH_RUNTIME.md) and the
[engineering report](../docs/research/results/task008-depth-2026-10-19.md).

Root npm scripts expose development, quality, build, and infrastructure commands.
`api.mjs` invokes the pinned Maven wrapper on Windows and Unix, accepts only fixed
tasks, runs in the API directory, and propagates failures. Core tasks select the
independent guardian-core POM with Maven's -f option; no API dependency or parent
inheritance is introduced. No system Maven
installation is needed. Run `npm run` to list tasks; see the root README for setup.

`doctor.mjs` checks runtime prerequisites. `security.mjs` enforces the documented
dependency policy. `smoke.mjs` checks the built applications together using temporary
loopback ports and cleans up its own processes and temporary JAR. `npm run verify`
runs these in order; Docker is not required.

Task006B local research tools: `evaluation_dataset.py` exports timestamp-sampled frames, imports COCO annotations and validates reviewed manifests; `qualify_detectors.py` writes empirical operating-point JSON/CSV/PR plots from successful hash-bound runs. See [workflow](../docs/perception/REAL_WORLD_EVALUATION.md). Both are included in lab lint/format checks. Plotting uses the optional pinned matplotlib dependency.

`motion_benchmark.py` compares bounded LK/DIS and optional prototype exclusion boxes on hash-verified local frame pairs. Outputs contain aggregate/compact observations, not raw images or private paths. Existing output files are never overwritten. See docs/motion/MOTION_EVALUATION.md for commands and evidence limits.
