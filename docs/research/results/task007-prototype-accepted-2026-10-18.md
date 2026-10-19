# Task007 closeout under the accepted prototype scope

Date: 2026-10-18. The user explicitly accepted prototype data quality, authorized
removing unusual labels, and deferred refinement. This changes the local progression
gate; it does not establish independent tracking accuracy or production safety.
Task008 has not been started.

## Data cleanup

Created `datasets/tracking_v1/sentinel-track-review-prototype.json` from the submitted
review. Removed all 31 suspect TRAIN reference annotations; retained 12,008 annotations
over 300 frames. All other boxes, labels, IDs, timestamps and metadata are unchanged.
The original review and draft remain intact. The transformation is recorded in the
local `prototype-cleanup.json`, including each removed annotation and source hashes.

Prototype SHA256: `7cf05f6ccbd11e671a6fbc6e8d382dcad2afc9095aed71046eb732888ef4900a`.
Structural validation and image provenance checks passed. The private files remain
Git-ignored. No media upload, dependency change or environment rebuild was involved.

TRAIN was selected because the spot-check established a false TRAIN label and the
user requested simple prototype cleanup. Not all 31 instances were individually
proven wrong. Removal can leave a real object absent from the reference; no replacement
boxes or identities were invented. Detector predictions were not filtered, so a
predicted TRAIN can still contribute a false positive. This is a documented data
curation policy, not a model accuracy improvement.

## Evidence and research choice

Both detector caches are evaluated against the same cleaned reference, with five
tracker/predictor combinations at 5 and 2.5 Hz across three clips: 60 runs total.
The [JSON](task007-prototype-accepted-2026-10-18.json) contains per-class metrics,
full counts, configuration and provenance; the [CSV](task007-prototype-accepted-2026-10-18.csv)
summarizes clip-local counts across clips. Identity F1 is computed from summed
identity counts, not by averaging clip percentages.

Prototype reference agreement at 5 Hz (all three clips, 12,008 reference observations):

| Detector | Tracker   | Predictor  | Identity F1 equivalent | ID switches | Fragments |
| -------- | --------- | ---------- | ---------------------: | ----------: | --------: |
| PicoDet  | IoU       | Alpha-beta |                   .225 |       1,407 |     1,021 |
| PicoDet  | Motion    | Alpha-beta |                   .262 |       1,215 |     1,000 |
| PicoDet  | Motion    | Kalman     |                   .208 |       1,243 |       990 |
| PicoDet  | Two-stage | Alpha-beta |                   .274 |       2,091 |     1,158 |
| PicoDet  | Two-stage | Kalman     |                   .198 |       1,768 |     1,260 |
| YOLOX    | IoU       | Alpha-beta |                   .141 |         586 |       574 |
| YOLOX    | Motion    | Alpha-beta |                   .166 |         540 |       581 |
| YOLOX    | Motion    | Kalman     |                   .148 |         469 |       499 |
| YOLOX    | Two-stage | Alpha-beta |                   .164 |         630 |       672 |
| YOLOX    | Two-stage | Kalman     |                   .141 |         575 |       596 |

These are weak agreement/continuity results, not evidence that tracking quality is
solved. Two-stage PicoDet has higher identity F1 but also more switches than motion-only;
YOLOX motion-only slightly leads its two-stage baseline. The prototype can progress
with this limitation explicit, but no reliable-identity claim or unbiased winner is justified.

All scores are **USER_ACCEPTED_PROTOTYPE_NOT_QUALIFICATION**. Most IDs still originate
from tracker proposals accepted unchanged by the user, so this is model-assisted
agreement evidence with bias toward the proposal-generating tracker. Removed reference
objects and UNKNOWN scenario labels further limit interpretation. It does not measure
independent real-world identity accuracy, high-motion/crowd robustness or safety.

Retain **two-stage association with alpha-beta prediction** as the Task008 prototype
input. It already supports low-confidence recovery and has the measured 600-second
pipeline evidence. This is continuity with a tested implementation, not a claim that
it wins an unbiased accuracy comparison. IoU, motion-only and Kalman alternatives
remain configuration-selectable behind the same contract.

## Verification and performance

Immediately before this data-only cleanup, `npm run verify` passed again: **420 tests**
(189 core, 204 lab, 24 web, 3 API), static checks, builds, dependency-security policy
and production smoke checks. No application/tracker code changed in this cleanup.
New checks validate the prototype file, enforce exactly the specified removal,
check ignored-file handling, rerun both cached evaluation matrices, and check
documentation formatting and Git whitespace.

The final optimized 600-second replay remains valid evidence for the unchanged code:
zero failures, queue peak one, tracker P95 24.41 ms, sampled process-tree peak RSS
219,615,232 bytes. The detector delivered **1.395 Hz against 5 Hz requested** under
desktop load. Prototype progression does not remove this throughput limitation.
See the [engineering report](tracking-benchmark-2026-10-18.md) for full evidence.

## Architecture assessment and status

**Architecture: 8/10 for a local research/prototype foundation.** Detector and tracker
interfaces are replaceable, results are immutable, temporal/spatial contracts are
explicit, state is bounded, and model runtimes stay out of core/web/API. Future depth
can join source/frame/time/track keys without exposing estimator internals. This is
a subjective engineering assessment, not a guarantee of arbitrary future changes.

Deferred refinement: independently corrected IDs/classes/missed objects; scenario
and occlusion labeling; additional recordings; target-hardware cadence; production
rights, deployment and assistive safety validation. Prototype metrics must not be
used later as independent qualification or as physical velocity/collision evidence.

**TASK007 COMPLETE FOR THE USER-ACCEPTED PROTOTYPE SCOPE: YES.**

**READY TO START TASK008 AS LOCAL PROTOTYPE WORK: YES.**

**ORIGINAL INDEPENDENT ACCURACY QUALIFICATION: NOT ESTABLISHED.**

**PRODUCTION SAFETY VALIDATED: NO.**

Task008 is not started by this closeout. The earlier stricter annotation blocker is
superseded by the user's explicit prototype scope, not by a fabricated validation pass.
