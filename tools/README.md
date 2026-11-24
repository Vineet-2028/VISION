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

Task010 tools: `export_pidnet.py` validates pinned sources/checkpoints and exports local ONNX; `semantic_benchmark.py` prepares bounded model proposals; `semantic_review.html` supports local partial-mask review; `evaluate_semantics.py` rejects unreviewed truth; `semantic_replay.py` measures bounded PTS-sampled replay. See [review instructions](../docs/segmentation/SEGMENTATION_EVALUATION.md). Models and data remain local and ignored.

`world_benchmark.py` measures bounded world-model scaling and local full/partial pipeline replay. It reports source ages, update/snapshot timings, entity/history/region peaks and sampled process RSS without raw images or private paths. See [Task011 runtime](../docs/world-model/WORLD_MODEL_RUNTIME.md).

`corridor_benchmark.py` adds bounded geometric-compute measurements, relation/mode counts, world-update intervals and optional local debug overlays. Existing report paths are never overwritten. `--overlays` explicitly creates up to eight private PNGs; default measurements export no imagery. See [Task012 runtime](../docs/corridor/CORRIDOR_RUNTIME.md) and [evidence limits](../docs/corridor/FREE_SPACE_EVIDENCE.md).

# Task013 trajectory benchmark

`trajectory_benchmark.py` measures bounded synthetic fit/stress cases or a private local replay. `--evaluate` compares frozen predictions to later same-entity tracker observations; these are biased research proxies, not reviewed truth. `--overlays` explicitly writes at most eight local PNGs. See `docs/trajectory/TRAJECTORY_RUNTIME.md`. Choose a new output filename for each run. Do not run Maven clean while the replay JVM owns Guardian's JAR.

# Task014 interaction benchmark

`interaction_benchmark.py` measures geometry/Guardian bridge latency, bounded stress and full replay. `--evaluate` freezes the prediction-time corridor and compares later observed same-ID tracks, reporting censoring and overflow. These are tracker proxies, not collision or physical TTC/CPA accuracy. `--overlays` writes at most eight private debug images. See [runtime](../docs/interaction/INTERACTION_RUNTIME.md); preserve previous results by choosing fresh output paths.

## Task015 risk evaluation and review

`risk_benchmark.py` measures isolated rule latency, stress, replay distributions,
preselected threshold sensitivity and tracker-proxy coverage. `risk_review.py`
prepares 30 draft temporal windows and serves them read-only on loopback.
No draft becomes ground truth automatically. See [runtime](../docs/risk/RISK_RUNTIME.md).

## Task016 attention prototype

Optional attention consumes risk contracts and produces explicit SILENT/ANNOUNCE/
REPEAT/ESCALATE intents. No speech is generated. See docs/attention for episode,
quality, cooldown, global-rate and Task017 integration rules; tools/attention_benchmark.py
and tools/attention_review.py provide local measurements and draft human review.
Task014 proxy recall remains 5.8%; human usefulness and production safety are unvalidated.

Task016 evidence: [architecture](../docs/attention/ATTENTION_ARCHITECTURE.md), [runtime and review instructions](../docs/attention/ATTENTION_RUNTIME.md), and [completion report](../docs/research/results/task016-attention-2026-10-24.md).

## Task017 alert presentation

Optional deterministic text alerts follow attention. See docs/alerts/ALERT_ARCHITECTURE.md and docs/alerts/ALERT_EVALUATION.md for contracts, limitations and offline review commands. No audio hardware, new ML or cloud service is required. Task018 evaluates this frozen loop; no Task019 or rescue features are included.

Task017 verification and remaining limits: [full research report](../docs/research/results/task017-alerts-2026-10-25.md).

## V0 rescue measurements

- `rescue_cadence.py`: sequential short pilots with explicit configuration changes.
- `rescue_gpu_probe.py`: isolated CUDA request, CPU fallback and node-placement audit.
- `rescue_profile.py`: per-stage timing/age and first freshness-failure records.
- `rescue_tracking.py`: fixed-reference tracking continuity diagnostics.
- `rescue_export.py`: versioned structured local demo output from completed runs.
- `v0_review.py --rescue-from <original-manifest> --packet <new-directory>`:
  preserve the original 30 windows and prepare unanswered human review fields.

Use new output directories. No tool may silently overwrite canonical Task 018
evidence or turn a draft review into human validation. See [rescue documentation](../docs/rescue/V0_RESCUE_ARCHITECTURE.md).
