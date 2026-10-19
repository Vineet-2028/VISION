# Experiment log

No R&D experiments have been performed or claimed in Task 002. Deterministic
unit tests validate software equations; they are not device/model experiments.
Copy the template below for each actual run. Preserve failed and inconclusive
results, raw artifact provenance, and configuration so others can reproduce them.

## Template

- Experiment ID:
- Date:
- Hypothesis:
- Code/model version (commit, artifact digest):
- Device (hardware, OS, runtime, power mode, thermal state):
- Dataset/scenario (version, split, provenance, consent/license):
- Configuration (parameters, seeds, rates, calibration):
- Metrics (definitions, units, sample counts, P50/P90/P95/P99 where relevant):
- Baseline and pre-registered decision criterion:
- Result (raw artifact link; include failures):
- Interpretation (uncertainty, confounders, limitations):
- Decision:
- Next experiment:

Keep captured sensor/user data out of Git. Follow an approved retention/access
policy before collecting any personal data.

## RND-DET-006C — local first-person preparation and replay

2026-10-17. MEASURED: 44,965 decoded frames from one 1,498.833-second recording;
458 review candidates, 60-second split guards, deterministic PTS/hash sampling.
12,328 YOLOX/PicoDet proposals remain DRAFT_MODEL_ASSISTED, not ground truth.
Model/source hashes and commands are recorded in the private dataset inventory,
proposal provenance and `benchmark-results/task006c/` artifacts.

The first sustained PicoDet replay exited normally but processed zero frames:
decoder catch-up starved processing. This is retained as failed evidence. Bounded
catch-up and a regression test were added. See the dated Task006C report for reruns,
verification and limitations. No training, held-out scoring or Task007 was started.

## RND-DET-006C — reviewed qualification continuation

2026-10-18. The preceding paragraph is historical. All 458 user-reviewed flags and
the user-confirmed SHELTER correction were imported; schema3 contains 12,324 P0
objects and one context annotation. All six viable candidates completed calibration,
froze operating points, then completed TEST without retuning. PicoDet-S416/.25 is
the provisional research primary; YOLOX-Nano416/.15 is fallback. Model-assisted
annotation bias remains explicit. No training was triggered and Task007 was not started.

YOLOX at the frozen threshold completed 600 seconds of source under concurrent
qualification load: 2,696 detector outputs, zero failures, queue depth one. A later
60-second 10 Hz request achieved 10 Hz; 15 Hz achieved only 11 Hz. These are desktop
observations, not production guarantees. Portable aggregate results and artifact
hashes are in `results/task006c-reviewed-2026-10-18.json`; the adjacent Markdown
report records the current verification and decision. No private footage was uploaded.

## RND-TRK-001–015 — Task007 temporal tracking

2026-10-18. Implemented bounded, detector-independent image-space tracking with
IoU/motion/two-stage policies and alpha-beta/Kalman predictors. Nineteen synthetic
runs and sixty cached real runtime runs are recorded in the
[Task007 report](results/tracking-benchmark-2026-10-18.md). Eight measured realtime
runs include two successful 600-second replays; the final optimized run reports
zero failures and two explicit gap resets. Requested detector rates were not met.
All 420 repository tests and full verification passed.

The [15-entry register](tracking-experiments.md) distinguishes measured engineering
from pending identity quality. Three 20-second clips yield 300 draft review frames
and 727 proposed IDs. Human correction is required before real identity metrics,
tracker selection or Task008 approval. No Task008 implementation was started.

Subsequent user scope change: the user accepted prototype data quality and asked
to remove unusual labels while deferring refinement. A separate prototype review
removes 31 suspect TRAIN annotations and retains 12,008 annotations; the submitted
review remains unchanged. Both detector comparisons use this same copy. The
[prototype closeout](results/task007-prototype-accepted-2026-10-18.md) records the
limited acceptance, provisional tracker and current progression status. This
supersedes the earlier annotation blocker only for local prototype work. Independent
accuracy and production safety remain unvalidated. Task008 has not started.
