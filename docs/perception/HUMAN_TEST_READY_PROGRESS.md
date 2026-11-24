# Human-test-ready pass — October 29 checkpoint

Status: IN PROGRESS. No release profile is frozen; Task019 has not started.

Latest: [October 29 continuous A/B closure checkpoint](ALPHA_CLOSURE_CHECKPOINT.md).
The archived 3,000-update pair verified identical non-presentation behavior,
with 60 generic outputs in A versus 54 generic and 6 specific in B. Current code
adds immutable lineage and fixes a score-basis alias split; final-revision
qualification remains pending. The result is not historical 60-event recovery.

## October 29 real PicoDet semantic integration

The opt-in real PicoDet producer now supplies generic observations with separate
source validity, score basis and uncalibrated semantics. Independent group fusion
and specific/group/generic presentation selection are implemented. Defaults are
not automatically adopted. See [the detailed A–K probe report](ALPHA_PICODET_SEMANTIC_PROBE.md).

A CPU context probe completed all 354 exact population frames plus 220 context
frames through the real detector and Guardian stages. At the frozen 60 targets,
declared overlap association found 18 specific-stable states, 3 group-stable,
34 unstable and 5 unmatched. The whole new schedule accepted 3 specific and
57 generic text outputs; these are not a proven one-to-one match to the frozen
60 alerts, so no qualified 60-to-57 recovery claim is made. All 34 unstable targets
had fewer than three qualifying same-concept observations in their retained evidence.

Canonical event scoring preserves all 188 events/5,313 observations. At least one
associated record exists through entity/track/world/corridor/trajectory/interaction/
risk/attention for 187 events. These are record-coverage proxies, not correctness.
133 events have some specific-stable evidence and 64 have some group-stable
evidence; these counts overlap. Six events have an accepted alert at a reference
frame. GPU/enricher selection, continuous-cadence exact-cohort recovery and final
Alpha qualification remain pending.

## October 29 semantic-loss investigation

The new continuation prioritizes semantic propagation before more model research.
See [the forensic report](ALPHA_SEMANTIC_LOSS_FUNNEL.md). An executed, hash-bound
SemanticEventLedger covers all 60 original alerts and eight stages per event.
All 60 original track/world categories remain present; all 60 original intents
record SEMANTICS_UNAVAILABLE. Original detector-box links are exact for 38 events;
22 remain unknown. This is distinct from the later 60/60 overlap proxy.

Historical traces omitted semantic evidence, so the first loss stage cannot be
retroactively established from those records. New schema-2 replay traces preserve
that evidence/provenance and world fusion state. Attention now records explicit
rejection reasons without relaxing its existing gates. No improved alert count
or completed propagation qualification is claimed yet. All 612 frozen baseline
archive hashes were reverified with zero mismatches on October 29.

No GPU inference ran during this investigation. Isolated GPU screening remains
pending; preserve the 2 GiB system-RAM reserve and announce duration before runs.

October 29 verification: `npm.cmd run verify` passed in
`benchmark-results/v02/alpha-semantic-verify-01.log`: 193 Guardian tests, 1,217
perception tests, web checks/build, API tests/build/static analysis, npm security
and production runtime smoke. An earlier local HTTP review test encountered a
connection-aborted error; its isolated rerun and the subsequent full run passed.
The 26 targeted semantic-ledger/authorization tests also passed. Android was not
changed or rerun. `git diff --check` passed with line-ending notices only.

## Implemented in this pass

- Read-only semantic dependency audit, followed by fixes for UNKNOWN generic
  objects missing from motion masks and surface occupancy. Both detection and
  observed-track paths retain these physical regions.
- Exact source-frame decoding and hash-bound comparisons across all 60 rescued
  alerts and 188 canonical events: 354 unique frames, 5,313 reference observations.
  No successful-frame sampling and no denominator changes.
- Grounding DINO Base assets pinned to revision
  `12bdfa3120f3e7ec7b434d90674b3396eccf88eb`, safetensors only, verified tokenizer
  files, local-only inference and no remote repository code. Research teacher
  outputs remain MODEL_PSEUDO_LABEL.
- Separate CUDA research runtime: torch 2.11.0+cu128 and torchvision 0.26.0+cu128.
  Official wheel URLs and SHA256 values are in the ignored installation report.
  The existing development environment was not replaced.
- Opt-in `camera_view_health` configuration now gates the actual Pipeline.
  UNUSABLE/UNKNOWN input publishes unavailable capability with original timestamps,
  skips inference/reasoning and clears pending alerts. Recovery resumes processing.
  Recorded view-health results use schema 13. The rescued configuration is unchanged.
- Separate user-motion-heading evidence, including source frame, coordinate frame,
  age, quality and uncertainty. Visual travel uses the static-point convention
  correctly; it is not optical-axis direction. Missing rigid-mount confirmation,
  ground orientation, usable translation or freshness gives UNKNOWN. The current
  video has no confirmed mount/gravity evidence, so this does not authorize body
  heading. Corridor integration and unusual-mount evaluation remain unfinished.

## Completed CPU screening

| Model                               | Named overlap proxy /60 | Event overlap proxy /188 | CPU call P95 |
| ----------------------------------- | ----------------------: | -----------------------: | -----------: |
| Rescued PicoDet settings            |                      60 |                      188 |     107.3 ms |
| YOLOE-26n prompt-free               |                      37 |                      187 |    1114.7 ms |
| YOLOE-11s prompt-free               |                      42 |                      184 |    1058.1 ms |
| YOLOv8s-Worldv2 embedded vocabulary |                      41 |                      185 |     710.9 ms |

These are same-frame detector proxies, not semantic accuracy, tracking continuity,
authorized speech or the historical realtime stage funnel. In particular,
PicoDet's names were available even though the rescued runtime produced 60 generic
alerts. This makes temporal semantic authorization a candidate improvement; it
does not establish that the names are correct. New models are not adopted.

Teacher prompts are the top 32 observed candidate concepts by configured frequency,
including questionable concepts. They are recorded as adaptive research queries,
not product branches or verified object classes. No external images or large
training datasets were downloaded. No training was started.

## GPU operation and interruption

The original teacher CPU run was intentionally stopped after its measured cost
made the full run impractical. CUDA teacher execution was verified on the RTX 3050
6 GB; observed memory was approximately 2.6 GB. Its first GPU process ended without
a completion marker at 234/354 frames; no error explained that termination.

The remaining frames completed in a separate artifact using exact ordered-prefix
validation, preserving the first output. Old rows lacked an embedded configuration
manifest; their binding is documented from this session's original command and
unchanged pinned inputs, not claimed as cryptographically embedded provenance.

GPU runs report an ETA before launch, enforce a PyTorch allocation fraction of at
most 85%, retain 2 GiB of free system RAM, and have an explicit processing time cap.
The resumed segment has a 12-minute cap. A stopped run retains completed rows;
only a complete population receives a COMPLETE summary. Reported resumed GPU peak
covers the final process segment, not an invented peak for the earlier process.

## Completed teacher comparison and robustness follow-up

The resumed teacher completed all 354 frames. Final-segment peak reserved VRAM
was 2,592,079,872 bytes; no earlier-segment peak is inferred. Its named-overlap
proxy was 38/60 and event overlap 179/188. The five-model comparison preserves
all denominators and has 48/60 alerts requiring review because of disagreement
or missing names. This is not semantic accuracy or automatic human validation.
Artifacts: `benchmark-results/v02/human-ready-comparison-01/`.

The GPU screening shortlist is YOLOE-11s (highest candidate named overlap) and
YOLO-World (lowest candidate CPU latency). Neither is adopted. YOLOE-26n is
excluded from deeper screening at this checkpoint. Teacher remains offline only.

Candidate GPU runs now persist configuration before inference, enforce a bounded
processing duration between calls, require 2 GiB free system RAM, and verify the
executing predictor and output tensor device. The first GPU attempt exposed an
incorrect check of the library's original CPU model copy; this was corrected.
The second stopped during warmup at the RAM reserve. Neither attempt produced
a complete result. No user applications were terminated to make room.
YOLO-World subsequently completed 106/354 frames before the same free-RAM guard
stopped it. That partial artifact is not included in qualification metrics.
GPU memory returned to 0 MiB after termination. GPU screening needs more available
system RAM under the same reserve; no VRAM exhaustion was observed.

An optional entity-semantic provider exception now quarantines that provider for
the session, exposes an unavailable warning, and lets physical entity processing
continue. Arbitrary exception text is not recorded. Geometry/association contract
violations still fail explicitly. Failure injection verifies all twelve frames
complete with entities retained and the worker cleaned up. Hung native calls
remain a separate unresolved process-isolation issue; this change handles raised
exceptions, not forcibly interrupting native code.

## Verification and remaining gates

The complete repository verification passed in `human-ready-verify-01.log`,
including the camera-health and heading integration. After the benchmark controls
and semantic-provider failure isolation, `npm run check:lab` passed formatting,
lint, static typing and all 1,208 tests (`human-ready-lab-03.log`). The targeted
failure-injection and benchmark-integrity run also passed all 22 tests. No new
web, backend or Android implementation changes were made in this follow-up.

Remaining: isolated GPU candidate
qualification; actual runtime semantic adapters/profile; data-driven broad-group
resolution; arbitrary-roll and rotated-video experiments; heading/corridor
integration; full-video, 18,000-frame and ten-minute realtime comparisons; final
adversarial review, release profile and A–BB report. A candidate screen does not
satisfy full pipeline qualification.

HUMAN_TEST_TECHNICALLY_READY: NO

CONTROLLED_ALPHA_DEPLOYMENT_READY: NO

HUMAN_USEFULNESS_VALIDATED: NO

PHYSICAL_ACCURACY_VALIDATED: NO

PRODUCTION_SAFETY_VALIDATED: NO
