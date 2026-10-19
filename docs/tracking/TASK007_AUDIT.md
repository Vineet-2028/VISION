# Task007 adversarial audit

Current scope: the user accepted prototype-quality annotations and deferred their
refinement. The [prototype closeout](../research/results/task007-prototype-accepted-2026-10-18.md)
supersedes the annotation blocker for local prototype progression only. The accuracy,
throughput and safety limitations in this audit remain applicable.

Date: 2026-10-18. Scope includes the existing Task001–006 boundaries and the new
tracking contracts, estimator, assignment, pipeline integration, review tooling and
evaluation. Initial inspection was read-only. This is a local engineering audit,
not assistive-product safety certification.

## Findings

### CRITICAL

No critical code issue identified in this pass. **Ground-truth integrity gate:**
`datasets/tracking_v1/draft.json` contains machine-proposed IDs. Using these as truth
would make identity scores circular. `tracking_dataset.py` and the benchmark CLI
reject unreviewed inputs; real runtime-only reports return null identity metrics.
Human correction remains mandatory, not a software fix or optional approval.

### HIGH

- **Endurance investigation, repeated verification passed:** two initial primary-detector tracking runs failed,
  at approximately 22 and 140 seconds. They are excluded from successful evidence.
  The private diagnostic runs and final result are recorded in the dated report.
  Subsequent instrumented offline/realtime runs and two measured 600-second runs
  passed. The final optimized run had zero failures and two explicit forward-gap
  resets. The original failures' exact cause remains unproven, not silently erased.
- **Fixed — forward-gap integration:** `pipeline.py` previously passed arbitrarily
  separated processed frames into a tracker that correctly rejects steps over five
  seconds. Dropped frames or a suspended process could therefore terminate replay.
  A regression now exercises a deterministic six-second gap. The owner
  now explicitly resets on same-clock forward gaps, emits retirement/reset metadata
  and preserves serial uniqueness. Regressions and clock mismatch still reject.
  The original two failures lacked detailed traces, so their exact cause is not
  retrospectively proven; final repeated replay evidence is required separately.
- **Fixed — evaluator assignment objective:** `tracking_evaluation.py` previously
  used a dummy penalty that could prefer one perfect overlap over two valid matches.
  This undercounted recall and distorted tracker comparison. Dummy cost now exceeds
  all possible valid overlap costs; a hand-computable ambiguous-match regression
  proves maximal cardinality before overlap quality.
- **Fixed — cleanup isolation:** `pipeline.py` now catches tracker-close failure
  and still emits completion/finalizes recording. A failing-close fixture verifies
  a FATAL manifest and cleared state instead of abandoned recording.

### MEDIUM

- **Annotation and scenario coverage:** `datasets/tracking_v1/README.md` and
  `tracking_benchmark.py`: three clips share one recording and assisted proposals.
  Crowd, high-motion, small-object and occlusion quality cannot be inferred from
  unreviewed labels. Review and inspect these strata; collect independent clips
  before generalization claims. No held-out tracking qualification is claimed.
- **Prediction limitations:** `tracking_motion.py`: constant-velocity box extent
  can become invalid during rapid changes. Such tracks retire with a diagnostic,
  not silent clamping. This can fragment IDs. Measure reviewed failures before
  changing the motion model; no long-term ReID or ego-motion is implemented.
- **Synchronous native work:** existing decoder/inference and bounded pure-Python
  assignment are not hard-real-time or preemptible. Latest-frame/staleness policies
  bound retained work, not execution deadlines. Measure on the target platform.
- **Recording cost:** `recording.py` serializes bounded observation history when
  explicitly enabled. It may reduce throughput; use default recording-off for
  ordinary replay and measure recording-on workloads separately.
- **Fixed — redundant association work:** `tracking.py` reconstructed and validated
  the same predicted box inside every matrix pair. Profiling sampled those NumPy
  reductions during a slow comparison. Association now reads the already-validated
  prediction once stored per track/update. Matching inputs are unchanged; all
  regression tests and both real cached matrices were rerun. Host load prevents
  attributing a precise speedup ratio to these separate timing runs.

### LOW

- **Fixed — zero-score evidence:** `tracking.py` ignores zero-confidence proposals
  even if thresholds are configured to zero, avoiding division by zero in category
  voting. Regression added.
- **Fixed — estimator covariance:** `tracking_motion.py` clears position cross terms
  when alpha-beta resets position uncertainty, preserving a PSD diagnostic proxy.
  Positive weighted correction also avoids subtractive cancellation. The proxy is
  explicitly not a calibrated probability.
- **Fixed — review navigation race:** `tools/track-review.html` ignores stale image
  load callbacks and clears a partial drag when navigating. Rapid navigation cannot
  apply an old load callback to the current frame. JavaScript syntax checked; native
  browser interaction remains a manual verification item.
- **Privacy limit:** Git ignores do not replace local disk access controls. Review
  images and opt-in recordings are sensitive local artifacts. No network upload,
  face identity, embeddings or cross-session recognition was added.

## Architecture and verification

The [integration audit](../architecture/TASK001_007_INTEGRATION_AUDIT.md) rechecks
module/time/geometry boundaries. NumPy was already a direct dependency; no new
framework or model is added. Tracker imports contain no detector runtime. Config
is strict/frozen; state and snapshots have separate ownership. Matrix sizes are
bounded, raw frames are not retained, and thread ownership is checked.

Final `npm run verify` passed: 420 tests (189 core, 204 lab, 24 web, 3 API), strict
mypy on 34 modules, Ruff, ESLint/strict TypeScript, Spotless/SpotBugs, builds,
dependency-security policy and production smoke checks. Pip consistency,
Prettier, editor JavaScript syntax and `git diff --check` passed. See the
[dated report](../research/results/tracking-benchmark-2026-10-18.md) for source
hashes, runtime measurements, earlier excluded failures and remaining gates.

Private failed/debug artifacts remain under `benchmark-results/task007`; they are
not rewritten as successful runs. No real identity metric is derived from draft
IDs. Final selection/Task008 remains blocked on reviewed temporal ground truth.
