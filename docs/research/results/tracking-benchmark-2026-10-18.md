# Task007 engineering report and review handoff

**Historical report:** the user later accepted prototype data quality and authorized
suspect-label removal. See the [prototype closeout](task007-prototype-accepted-2026-10-18.md)
for the current scope and status. The original stricter qualification gates and
measurements below are preserved as history, not rewritten as independent validation.

Date: 2026-10-18. **Implementation and local verification are complete; Task007's
real tracking-quality gate is NOT complete.** No Task008 work was started.

Review-import update: a 300-frame reviewed export was received and structurally
validated. A visual spot-check found an unresolved car-as-TRAIN label; its computed
scores are diagnostic only. See [review import audit](../../tracking/REVIEW_IMPORT_AUDIT.md)
for the exact correction and current ground-truth quality gate.

Evidence: [aggregate JSON](tracking-benchmark-2026-10-18.json),
[runtime CSV](tracking-benchmark-2026-10-18.csv),
[adversarial audit](../../tracking/TASK007_AUDIT.md), and
[local review instructions](../../../datasets/tracking_v1/README.md).
Private logs/configurations/caches remain under `benchmark-results/task007/`.
JSON records source/artifact hashes, denominators, configuration and timing windows.

## A. Pre-task audit

Read-only inspection checked Task006 reports, detection/frame/time contracts,
scheduler, core geometry/motion boundaries, lab ownership, recording, schemas,
verification scripts and existing tests before implementation. DetectionBatch
retains source identity, observation PTS, original-image boxes and provenance.
Vendor tensors stay inside adapters; successful empty output differs from failure.
PicoDet and YOLOX remain configuration-selected research models. Physical camera
calibration/exposure is not established by screen-recording PTS.

## B. Files changed

New lab modules: `tracking_types.py`, `tracking_config.py`, `tracking_motion.py`,
`tracking_assignment.py`, `tracking.py`, `tracking_dataset.py`,
`tracking_evaluation.py`. Three tracking test modules were added. Existing lab
config, contracts, pipeline, metrics and recording gained optional tracking.
`tools/prepare_tracking.py`, `tracking_benchmark.py`, `track-review.html` and the
lab runner provide preparation, review and verification. Documentation includes
seven tracking documents, Task001–007 integration, replacement contracts, research
register, dataset handoff and root/lab README updates. Ignore rules protect private
packets. Pre-existing Task001–006 uncommitted work was preserved; no commit created.

## C. Tracking architecture

DetectorAdapter → DetectionBatch → MultiObjectTracker → immutable TrackSet.
The lab owns mutable tracker state on one thread. Guardian Java remains authoritative
for camera geometry and physical motion. There is no detector vendor import in
tracking, no model/JVM startup per frame, and no new runtime dependency.

## D. Track contract

TrackId combines session and monotonic serial, independent of detector IDs. TrackSet
retains frame/source/time, tracker provenance, evidence status, immutable snapshots,
current retirements and diagnostics. Snapshots include observed/predicted boxes,
observation age, hits/misses, category evidence, bounded history and detector
provenance. Estimator matrices are not a downstream API.

## E. Lifecycle

TENTATIVE → CONFIRMED after configured consecutive observations; successful misses
make established tracks LOST. Observation-age expiry removes tracks. Removal IDs
are emitted without retaining session-long tombstones. Reset does not reuse serials.

## F. Motion model

Fixed `[cx,cy,w,h,vx,vy,vw,vh]`, actual observation-time dt, dedicated alpha-beta
and four independent 2×2 Kalman blocks. Kalman correction uses Joseph covariance
update. Invalid extents retire rather than silently clamp. Covariance/quality are
uncalibrated diagnostics. Pixel rates include camera motion and are not physical velocity.

## G. Association

Bounded deterministic global assignment uses IoU, normalized center displacement
and class disagreement penalty. Gates reject distant associations. Predictions are
validated once per track/update and reused across candidate costs. Near-identical
same-class duplicates are suppressed conservatively at .98 IoU; no complex merging.

## H. Two-stage / low-confidence recovery

High-score observations associate first. Low-score observations can recover unmatched
confirmed tracks, never start new tracks. Proposal floor .10 is separate from
publication thresholds .25 PicoDet / .15 YOLOX. Task006 frozen results are unchanged.

## I. Category stabilization

Confidence-weighted decayed category votes resist isolated flicker and permit
sustained changes. UNKNOWN and zero-score proposals do not create tracks.
The bicycle/motorcycle regression passes; real class-flicker improvement is unmeasured.

## J. Detector cadence decoupling

Tracking predicts on every processed frame, not only detector ticks. Scheduling
uses observation time. Direct tracker updates reject discontinuities; the pipeline
explicitly resets on same-clock forward gaps, reports old IDs removed and starts
new tentative IDs. Clock/source mismatch and regressions remain errors.

## K. Observed versus predicted semantics

NO_DETECTOR_RUN, SUCCESS, SUCCESS_EMPTY, FAILURE and UNAVAILABLE are distinct.
Unscheduled ticks do not count as successful misses. Failures reduce quality and
retain a public failure code. Predicted snapshots never claim a detector observation.
Raw recovery evidence may be SUCCESS while the separately published high-score
DetectionBatch is empty; this distinction is intentional and tested.

## L. Occlusion handling

Short-gap prediction/reassociation is implemented and regression-tested. After
time-based expiry, returning objects receive new IDs. Long-term re-identification
is neither implemented nor claimed. No invented boxes are requested for fully
hidden ground-truth objects.

## M. Bounded-state design

Defaults: 64 tracks, 128 admitted detections, 32 history entries per track. Hard
configuration ceilings: 128/256/128. Runtime assignment dimensions follow those
caps; offline identity assignment permits at most 512×512. No raw frames, per-track
threads or unbounded removed-track list. Overload emits diagnostics. A 1,000-frame
regression checks bounded state; cleanup is tested even when tracker close fails.

## N. Tracking dataset

Three 20-second TRAIN_DEV windows from the existing user-owned video, starting at
50/230/450 seconds, sampled at 5 FPS: **300 frames, 727 proposed clip-local IDs**.
They are correlated development windows, not independent held-out qualification.
Both detector caches use identical JPEG pixels. Preparation-time raw-video
predictions are retained only for proposals and not used as the fair comparison cache.

## O. Ground-truth status

**HUMAN_TRACK_GROUND_TRUTH_REVIEW_REQUIRED.** Every frame is DRAFT_TRACK_LINK.
Task006 box review does not establish persistent Task007 identity. Correct boxes,
classes, missed objects and temporal links; save `sentinel-track-review.json` using
the [local editor workflow](../../../datasets/tracking_v1/README.md). Validation
checks immutable source/frame/time/image hashes, unique per-frame IDs and review
status. It cannot certify the semantic accuracy of a human's review.

## P. Baselines compared

Nineteen analytical experiments and sixty real cached runtime runs compare IoU,
motion/global assignment and two-stage association, including alpha-beta/Kalman,
cadence divisors and confirmation/expiry sensitivity. Real identity scores remain null.

Synthetic analytical identity-F1 equivalent (not real-world performance):

| Policy                 | 25 Hz detections | 12.5 Hz | 5 Hz | 5 Hz switches / fragments |
| ---------------------- | ---------------: | ------: | ---: | ------------------------: |
| IoU                    |             .664 |    .578 | .517 |                    4 / 41 |
| Motion + alpha-beta    |             .907 |    .902 | .865 |                     1 / 6 |
| Motion + Kalman        |             .907 |    .902 | .885 |                     1 / 1 |
| Two-stage + alpha-beta |             .907 |    .902 | .881 |                     1 / 4 |
| Two-stage + Kalman     |             .907 |    .902 | .885 |                     1 / 1 |

The fixture includes crossings, class flicker, misses, low scores and isolated false
proposals. It does not establish a real-world winner. All counts/denominators and
per-class synthetic metrics are in JSON; identity F1 is explicitly defined, not an
official MOTChallenge/HOTA implementation.

## Q. Real-world metrics

Runtime/latency/state measurements are available. Real IDF1-equivalent, recall,
false-track and mostly-tracked/lost accuracy are **unmeasured**, not zero.

## R. ID switches / fragmentation

Synthetic counts appear above. Real results await reviewed IDs. The evaluator has
hand-computable switch, fragment, duplicate and maximal-match-count regressions.

## S. P0 track continuity

Per-class evaluation is implemented but real P0 scores are unavailable until review.
No continuity claim is inferred from generated track count or apparent persistence.

## T. Crowd results

Bounded many-detection and same-class crossing tests pass. Real crowded-frame
identity switches and duplicates need reviewed scenario labels and visual error analysis.

## U. High-motion results

Not measured against reviewed IDs. No ego-motion compensation exists; abrupt turns
can invalidate association. UNKNOWN scenario labels are not treated as HIGH motion.

## V. Occlusion results

Short and beyond-timeout synthetic regressions pass. Real correct recovery versus
wrong reassociation requires reviewed identity/occlusion labels.

## W. Small-object results

Pending reviewed size/identity error analysis. Prediction is not evidence that an
unobserved tiny object remains present indefinitely.

## X. Detector cadence results

CPU FP32, one detector thread, 416-pixel inputs; uncontrolled Windows desktop load.
Short runs overlap other experiments; the final endurance also overlaps repository
verification initially. Do not treat requested rates as achieved rates or compare
these timings as isolated model benchmarks.

| Run                     | Source duration | Requested detector Hz |   Achieved Hz | Failures |
| ----------------------- | --------------: | --------------------: | ------------: | -------: |
| Final optimized PicoDet |           600 s |                     5 |         1.395 |        0 |
| PicoDet short / repeat  |       60 s each |                    10 |  1.10 / 1.617 |        0 |
| YOLOX short             |            60 s |                     5 |         2.633 |        0 |
| YOLOX short / repeat    |       60 s each |                    10 | 2.733 / 3.833 |        0 |
| YOLOX short             |            60 s |                    15 |         2.817 |        0 |

These runs do **not** qualify sustained 5/10/15 Hz. Decoder catch-up and inference
consume substantial time. Target-machine throughput remains an explicit performance
limitation; no download/reinstall or new framework is justified by these measurements.
Cached real clips compare 5 and 2.5 Hz observation schedules; they do not fabricate
10 Hz ground truth from 5 Hz images.

## Y. Tracker latency and result age

Final 600-second primary replay tracker-only: P50 **10.89 ms**, P90 **21.10 ms**,
P95 **24.41 ms**, P99 **33.66 ms**, maximum **73.11 ms** (955 updates).
End-to-end published tracking result age: P50 **282.40 ms**, P95 **332.96 ms**,
P99 **934.00 ms** (954 results). Age maps source time to the realtime replay clock;
it is not merely tracker processing duration. Total tracker timings are measured;
separate prediction/assignment/snapshot substage distributions are not instrumented.

## Z. Long-run memory / stability

Final run covers 600 seconds, 18,001 decoded frames, 954 published processed frames,
17,047 drops and zero failures. One extra decoded boundary frame is counted as
USER_SKIP. One tracking update was abandoned before publishing. Queue peak one;
active track peak 64, lost peak 18, history peak 1,265, maximum serial 8,220.
Two forward gaps explicitly reset tracking; identities were not continued across them.

Sampled process-tree RSS: start **2,355,200 B**, peak **219,615,232 B**, end
**204,578,816 B**, 601 samples at one-second intervals, including JVM. The first
sample precedes initialization; its difference from the end is not a leak estimate.
One bounded run supports observed stability, not proof of indefinite leak freedom.
Two earlier failed runs are excluded. Instrumented offline/realtime reruns passed;
the original failures were not conclusively traced, and are retained transparently.

## AA. PicoDet-S compatibility

Real cached inference, all baseline policies and repeated live replay pass. Weights
and Task006 preprocessing remain unchanged. Selection is research-only.

## AB. YOLOX-Nano compatibility

Real cached inference, all baseline policies and 5/10/15 Hz requested replay runs
pass using its .15 publication threshold and the same tracker implementation.

## AC. Detector swap

Configuration changes runtime, reviewed weight hash and publication threshold.
Tracking source/contracts do not change. Identical JPEG inputs support the offline
comparison; live timings have different load histories and are not controlled rankings.

## AD. Task001–007 integration audit

001→002 **PASS**; 002→003 **PASS**; 003→004 **PASS**; 004→005 **PASS**;
005→006 **PASS**; 006→007 contract/runtime **PASS**, reviewed tracking quality
**PARTIAL**. See the [boundary audit](../../architecture/TASK001_007_INTEGRATION_AUDIT.md).
Full verification re-executed existing core, API, web and lab checks.

## AE. Component replacement audit

**PASS for implemented boundaries.** Detector data are vendor-free; tracker policy
changes preserve TrackSet. Configuration/provenance identifies research settings.
Future-consumer compatibility is a design assessment, not an executed Task008 test.

## AF. Future depth / ego-motion / world-model compatibility

Session/frame/time/box identity supports later depth joins. Motion/association can
be replaced behind the tracker protocol. Immutable observed/predicted snapshots
can feed a future world model without exposing filter matrices. None is implemented.

## AG. ReID decision

**INSUFFICIENT_EVIDENCE; do not add ReID.** Short-gap motion tracking is implemented;
appearance models require demonstrated reviewed failure cases and cost/privacy review.

## AH. R&D experiments

All fifteen RND-TRK entries have question, motivation, hypothesis, experiment,
metrics, decision criterion and status in the [research register](../tracking-experiments.md).
Pending human evidence is marked pending rather than invented.

## AI. Security / privacy

No model download, upload, telemetry, face recognition, embeddings or cross-session
person identity was added. Packets/media are ignored and local. The editor restricts
network access and uses frozen image paths. Config is strict; packet hashes and
input limits reject mismatched provenance. `npm run security` passes policy with
five reviewed development dependency entries; this is not a zero-vulnerability result.
Commercial model rights, native parity, deployment security and device safety remain
outside this local tracking approval.

## AJ. Adversarial audit

**CRITICAL:** no identified outstanding critical code defect; generated IDs must
never be used as reviewed truth. **HIGH, fixed:** forward-gap integration, evaluator
matching objective and tracker-close finalization. Historical runtime failures remain
disclosed rather than assigned a proven cause. **MEDIUM:** throughput, correlated
annotation evidence, motion-model limits, recording cost; redundant per-pair box
validation was fixed. **LOW, fixed:** zero-score voting, covariance reset, editor
load race. Remaining browser interaction and platform checks are below. Detailed
affected files, consequences and fixes appear in [TASK007_AUDIT](../../tracking/TASK007_AUDIT.md).

## AK. Test counts

**420 passing:** guardian-core 189, perception lab 204, web 24, Spring Boot API 3.
The previous 383-test baseline is preserved and extended with 37 tracking tests.

## AL. Full verification

Executed `npm run verify`: **PASS**. Includes doctor, Prettier, core/API Spotless,
SpotBugs and tests/builds; lab Ruff, strict mypy on 34 modules and pytest; web ESLint,
strict TypeScript, Vitest and production build; security policy; production API/web
health, eight concurrent requests and outage smoke checks. `pip check`, editor JS
syntax and `git diff --check` also passed. Hosted CI itself was not executed here.
Android is intentionally absent; Docker is optional and was not started.

## AM. PRIMARY_TRACKER_FOR_TASK008

**UNSELECTED pending reviewed evidence.** Two-stage alpha-beta is the configured
research candidate, not an accuracy-qualified winner. Synthetic results alone do
not justify choosing it over simpler motion association or Kalman.

## AN. Remaining risks and architecture rating

Subjective **architecture rating: 8/10 for a local research foundation**. Clear
ownership, immutable contracts, explicit time/units, bounded state and replaceable
adapters support future changes. The rating is reduced by lab-bound Python tracking,
synchronous native work, unvalidated throughput/identity accuracy and future contract
migrations. It is not a production-readiness or safety score.

Known unverified items: human track IDs; crowd/high-motion/occlusion/small-object
accuracy; independent recordings; interactive editor behavior in a real browser;
GPU/mobile performance; physical camera calibration; native parity/model commercial
rights; hosted CI and production deployment. Requested detector rates were not met.
No architecture can guarantee arbitrary future changes without regression testing.

## AO. Final verdict

**TASK007 COMPLETE: NO.**

**ENGINEERING QUALIFIED FOR TASK008: NO.**

**PRODUCTION SAFETY VALIDATED: NO.**

Blocker: **HUMAN_TRACK_GROUND_TRUTH_REVIEW_REQUIRED**. Review the prepared 300 frames
and 727 proposed IDs, then resume from the cached evaluation commands in the dataset
README. Compare real identity/failure cases and select the provisional tracker before
closing Task007. Rebuilding the environment or reselecting detectors is unnecessary.
