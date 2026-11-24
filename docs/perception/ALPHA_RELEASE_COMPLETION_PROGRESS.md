# Controlled Alpha release completion evidence

Updated 2026-11-05. This is an engineering work record, not a release freeze or
permission for unsupervised use. The final pre-human-review mission remains active.

## Trace overhead

`COMPACT_ALPHA_TRACE` is now the default for `tools/v0_replay.py`; `--trace-mode FULL`
retains detailed stage diagnostics. Continuous presentation-ablation runs still
default to full diagnostics. Their comparator rejects compact schema-3 records,
which omit fields and therefore cannot establish full stage equivalence.

Compact records retain current state, raw detector observations at their origin,
source identities, alert lineage, authorization reasons and expiry evidence.
Repeated observation payloads and track histories are omitted. Both synchronous
and asynchronous replay writers record logical UTF-8 bytes, serialization time,
write-call time, rows and queue metrics. Logical bytes exclude platform newline
translation; file size includes it. These times do not measure physical disk flush.

The two-second CPU comparison in
`benchmark-results/v02/alpha-compact-comparison-02.json` used identical source
identities and runtime hashes, with 60 updates in each run:

| Measurement                    |       Full |    Compact |
| ------------------------------ | ---------: | ---------: |
| Trace bytes                    | 25,642,450 | 11,803,344 |
| Bytes per update               |    427,374 |    196,722 |
| Mean instrumentation wall time |   54.37 ms |   27.41 ms |
| Delivered outputs              |          1 |          1 |

Trace size fell 53.97%. This is a short sequential CPU diagnostic comparison,
not a realtime throughput claim, semantic-equivalence result, or release gate.
It predates subsequent heading/roll additions. Diagnostic volume is still material;
final realtime qualification must include it.

## Heading integration

World consumption retains the supplied `UserMotionHeadingEstimate`. The corridor
uses it only when identity, timestamp, camera frame, source, quality, age and unit
direction checks pass, and supplied-ground geometry is available. Guardian performs
the ground projection and coordinate transforms. Heading provenance follows the
derived corridor; geometry stays explicitly degraded and physically unvalidated.

Missing or unusable heading retains the labeled camera-forward fallback with an
explicit reason. This does not claim camera-forward is user-forward. Semantic
worker snapshots preserve heading from the same update. The recorded video lacks
authorized rigid-mount/ground metadata, so it does not acquire a fabricated heading.
Phone metadata ingestion and full field-path qualification remain required.

## Arbitrary roll

Guardian now provides continuous-edge image-plane rotation with EXPAND, PAD and
CROP canvases. `RollCanonicalizer` applies the inverse of explicitly supplied
clockwise image roll and accounts for OpenCV's pixel-center convention. It keeps
one cached mapping, bounds output pixels, preserves grayscale channel dimensions,
and makes the result immutable. Pitch and yaw never become roll corrections.

EXPAND retains geometric source corners with an angle-dependent canvas. PAD uses
a fixed diagonal square. CROP retains original dimensions and can discard FOV.
Unknown/poor orientation leaves pixels unchanged and reports unavailability.
Scaled-source calibration is explicitly rejected until composition is supported.
Calibration remains in the original camera frame through inverse mapping; no
axis-aligned rotated intrinsics are invented. These are implemented primitives,
not yet the selected or qualified full-pipeline field orientation policy.

## Executed checks

- Previous full repository verification log reached final smoke success:
  `benchmark-results/v02/alpha-release-verify-01.log`: 1,254 perception tests,
  193 Guardian tests, 31 web tests, 3 API tests, builds/static checks/security/smoke.
  It predates arbitrary roll and the final snapshot/trace instrumentation edits.
- Final roll Guardian check: `benchmark-results/v02/alpha-roll-core-02.log`:
  195 tests, zero failures, Spotless and SpotBugs passed.
- Targeted roll/cardinal/heading/corridor/trace regressions: 159 passed after fixing
  a test point outside the 8-by-6 synthetic image. The initial failed test run is
  not counted as a pass.
- Strict mypy passed for 109 production Python files; Ruff checks passed.
- Complete perception verification after the roll/heading changes passed with
  1,298 tests: `benchmark-results/v02/alpha-roll-lab-01.log` (exit 0).
- Frozen baseline archive rechecked against all 612 manifest source hashes.

Those roll/heading checks did not launch GPU experiments. Subsequent GPU work is
recorded below. The 2 GiB reserve remains unchanged; no unrelated applications
were killed.

## Sequential GPU qualification continuation — November 4

The local CUDA smoke run `alpha-cuda-smoke-02` completed 20 updates over four
source seconds without the earlier NVRTC DLL warning. The existing local NVRTC
library is explicitly preloaded; no global driver/runtime replacement was needed.
Provider metadata alone is not per-node GPU execution proof. A separate profiling,
copy-inclusive I/O binding, graph-cache and FP16 experiment remains to be executed.

`alpha-compute-batch-01` stopped at the 2 GiB free-RAM reserve after approximately
645 seconds. It has no complete A/B result and is not qualification. GPU free
memory recovered to its observed baseline. After the user freed applications,
`alpha-compute-batch-02` started with 3.526 GiB free RAM and 6,001 MiB free VRAM.
Its authoritative status is `benchmark-results/v02/alpha-compute-batch-02/batch-status.json`;
starting a batch is not a passed gate. Engine sources remain unchanged between arms.

The sequence runs one model at a time: A, B, exact comparison, lineage-bound
residual extraction, then each optional candidate under a five-minute parent wall
limit. An interrupted candidate cannot count as complete screening or runtime
qualification. Optional enrichment is still not selected for the Alpha runtime.

Lightweight audit corrections made while the replay runs:

- Process supervision retains observed descendants after their launcher exits and
  terminates those owned processes. Three real-subprocess regression tests pass.
- Comparison rejects incomplete/empty runs, failed/dropped frames, writer drops,
  differing runtime metadata and missing physical-stage records. Fourteen admission
  and comparison regression tests pass.
- Residual extraction checks selected world identity against immutable lineage even
  when no observation payload exists. Seven residual tests pass. The final residual
  artifact is published atomically without replacing previous evidence.
- Historical October 29 documentation is explicitly labeled as historical so it
  cannot be mistaken for the current adapter implementation.

These 24 targeted tests passed with Ruff checks. They do not replace final full
repository verification or measured full-pipeline qualification. ADB currently
lists no physical device; camera, physical timing and Bluetooth tests remain pending.

## Completed semantic batch and follow-up repairs

`alpha-compute-batch-02` finished. Both arms completed all 3,000 updates without
frame failures or drops; their compared non-presentation stages matched. A delivered
60 generic outputs; B delivered six specific and 54 generic outputs. All 60 B
deliveries passed exact-lineage validation. The 115-file measured runtime is archived
and hash-verified in the batch directory. Historical 60/188 markers remain explicitly
unresolved; they were not substituted with current outputs or overlap proxies.

YOLOE and YOLO-World each completed 54/54 residual frames on CUDA. Grounding DINO
stopped at the system-RAM reserve and has no qualifying residual result. Optional
runtime enrichment remains NONE: research-only clearance, temporal marginal recovery
and contended whole-pipeline performance have not been established. See the
[semantic measurement report](../research/results/vision-alpha-semantic-qualification-2026-11-04.md)
for measured values, artifact paths and limitations.

The first optimization probe stopped at the RAM reserve after ten seconds, without
a qualifying result. On November 5, after the user freed RAM, the second probe started
with approximately 3.75 GiB free RAM and an eight-minute hard cap. It completed in
113.75 seconds (`alpha-gpu-optimization-02-process/process-summary.json`, exit 0).
All 20 sampled FP32 CPU/CUDA comparisons passed. The execution profile recorded
522 CUDA nodes and eight CPU nodes, rather than claiming every operator ran on GPU.
Copy-inclusive I/O binding passed parity; sampled P95 was 24.252 ms versus 31.058 ms
for ordinary session execution. These are 20 repeated last-frame detector calls,
not whole-pipeline tails. Graph-cache build/serialization was 425.765 ms and reload
462.741 ms; cache parity passed but startup did not improve. FP16 conversion failed
with recorded error type `Fail`; it was not adopted. Neither I/O binding nor caching
has been adopted without whole-pipeline evidence. FP32 remains selected.

After preserving both replay manifests and runtime sources, field-session repairs
made cached result age advance on every response, suppress results at 500 ms, require
exact admitted capture identity, reject replayed/old-session publications, prevent
clock resynchronization from regressing host capture time, and stop recording/events
on close. These changes postdate the measured A/B snapshot. All 32 field
protocol/session/gateway tests passed, including synthetic 50/100/250/500/1000 ms
transport delays; Ruff and strict mypy passed for the changed production module.
They do not constitute physical phone or end-to-end inference/TTS qualification.

Latest targeted tool checks: 15 admission/comparison, eight residual-analysis and
four process-supervision tests passed. Another 38 semantic expiry, entity-alert,
lineage and view-health tests passed. Final broad verification remains required.

## Orientation integration and realtime measurements — November 5

Frame-bound orientation now reaches the normal command-line/replay preprocessing
factory. GOOD total received-image roll and cardinal correction are alternative
paths, never added together. Detector coordinates inverse-map to the original
calibrated camera frame. Missing metadata remains unknown. The configuration is
opt-in; unsupported crop/resize/NCHW combinations fail validation. Metadata is
preserved in results and traces even when view health suppresses inference.

The complete perception check passed: 1,332 tests, Ruff formatting/lint and strict
mypy for 110 production modules (`alpha-integration-lab-02.log`, exit 0).

`alpha-realtime-01` is a detector-only ablation with active view-health and compact
trace. Its profile omits optical flow and segmentation, so it must not be directly
compared with the rescued full profile's 4.399 Hz / 567.211 ms P95. The distinction
is recorded in `alpha-realtime-01-scope.json`. `alpha-candidate-profile-02.json`
restores the rescued LK flow and CUDA PIDNet configuration, keeping depth absent
as in the rescued baseline. Full-profile realtime qualification remains required.

Android audit repairs are awaiting their build/test gate: malformed DNS hostnames
can no longer pass private-IPv4 validation by dropping nonnumeric segments; a late
TTS start callback for a superseded utterance no longer stops current speech. The
start event is labeled `APP_TTS_PLAYBACK_START_ESTIMATE`, not physical audio onset.
The uncertainty test now checks valid alerts on both accepted/rejected sides rather
than rejecting all fixtures for an unrelated invalid deadline. These changes do not
complete the pending phone/TTS integration or physical tests.

## November 5 full-profile and Android verification

The full recording replayed through PicoDet, LK flow, PIDNet and downstream
Guardian stages. The observed source endpoint was 1,498.8 s. The engine
processed 18,541 updates at 12.368 effective outputs/s with zero failed frames.
Latest-frame admission replaced 20,926 pending frames and skipped 5,498 before
conversion. The input queue peaked at one. The diagnostic writer dropped zero
rows and wrote 4,237,368,903 bytes. This capture size matters when budgeting disk
for qualification. The supervisor measured a peak process-tree RSS of
1,186,734,080 bytes and at least 5,777 MiB of free GPU memory at its five-second
samples. The source archive contains 115 files verified against the run manifest.

Within the first 600 s, the candidate published 6,300 updates (10.50 per source
second), including 6,287 attention outputs. P95 source-to-publication age was
257.657 ms against the historical rescued 567.211 ms. The full recording's P95
was 241.947 ms, P99 294.941 ms, and maximum 1,552.570 ms. The text sink accepted
37 specific, two group and 133 generic alerts. Zero deliveries reached their
deadline and 70 upstream candidates expired. No ordinary alert was delivered on
an unusable view. Different realtime admission across runs precludes an
event-by-event accuracy comparison.

The Android debug APK assembled, all eight FieldPolicy JVM tests passed, and
Android lint passed in a clean local build directory. OneDrive's read-only
generated test directory had stopped the earlier build. The Android README
documents the local build-directory override. The Android SDK tools emitted an
XML metadata version warning. Physical camera, audio and Bluetooth remain open.

The frozen and candidate offline arms both processed the exact 18,000 canonical
frame identities with zero failures. Each decoder also saw and excluded the
out-of-window frame at 600 seconds. The ordered identity hash was
`476169bbc238135f4e57e3f082f623dd8fa3e60ec5bfa810fb7710fef1cc44a1` in both
arms. The candidate delivered 11 specific, one group and 61 generic text events.
The baseline delivered 60 events without a recorded semantic level. The
candidate took 2,987.6 seconds for replay versus 1,011.5 seconds for the baseline.
The offline processing cost increased even though latest-frame realtime
publication improved. The baseline runtime emitted NVRTC lookup warnings, so
its offline elapsed time is descriptive and cannot isolate semantic overhead.

## Gate status after the November 5 qualification

1. Preserve the measured semantic-pair revision and distinguish it from subsequent
   integration changes during final qualification. Historical missing lineage cannot
   be repaired by inventing correspondence; optional research is not a release blocker.
2. All 21 rotated clip arms ran the complete engine, with 1,260 frames and zero
   failures. Track recovery varied by scene; see the [release](../releases/VISION_CONTROLLED_ALPHA_V1.md).
3. The engine is frozen. The field worker passed authenticated desktop loopback
   with synthetic camera inputs, fresh results and stale-result suppression.
4. The Android capture, orientation and speech paths and the web review interface
   are implemented. Website and field verification are tracked separately from
   the engine freeze.
5. Release limitations, pairing instructions and human-review instructions are
   available in `docs/releases`.
6. Physical phone/camera/audio/Bluetooth checks require real hardware; do not replace
   them with JVM tests or mark human review completed automatically.

The November 6 closure, executed verification, final audit and remaining physical
evaluation gates are recorded in the
[final release report](../research/results/vision-controlled-alpha-v1-final-2026-11-06.md).
Human usefulness, physical accuracy, production safety and unsupervised deployment
remain unproven. Task019 has not started.
