# Task 006B adversarial audit

## Read-only pre-task pass

Inspected the prior dated report, JSON/CSV, raw predictions, bounded error metadata,
dataset manifest, Task006 audit, adapters, metrics, replay clock/scheduler and
research decisions before making changes. Recomputed confidence 0.25 / IoU 0.50:

| Candidate     |  TP |  FP |  FN | Recall |  FP/100 |
| ------------- | --: | --: | --: | -----: | ------: |
| YOLO26n       | 129 |  37 |  83 | 60.85% |  102.78 |
| YOLO26s       | 152 |  54 |  60 | 71.70% |  150.00 |
| YOLO11n       | 132 |  47 |  80 | 62.26% |  130.56 |
| RT-DETRv2-R18 | 188 | 363 |  24 | 88.68% | 1008.33 |

The old report correctly disclosed diagnostic-only data and synthetic robustness.
It did not establish representative qualification. Prediction floor 0.05 could
not support 0.01–0.04 analysis. Adapter-only timing stopped before batch creation;
the benchmark's outer end-to-end timer did include it. Detailed output processing
was aggregated. No real-world dataset or representative long-video evidence existed.

## Implementation/reporting fixes and repeat review

- New runs explicitly capture predictions at 0.01. Analytical threshold tests compare
  the efficient prefix calculation against full greedy matching at every threshold,
  including duplicate detections and crowd absorption. Failure and wrong frame IDs
  are rejected, never counted as misses. FP budgets divide by evaluated frames.
- Operating-point selection uses actual grid points; no unreachable precision/recall
  is extrapolated. Same-set post-hoc threshold selection is prominently disclosed.
- Dataset export produces unreviewed drafts. COCO ignore/crowd flags reject malformed strings instead of coercing them to true; duplicate category IDs and image filenames are rejected. Validation checks class/positive area,
  original dimensions, bounded coordinates or explicit truncation, source/annotation/
  image hashes, duplicate images/boxes/observations, and sequence split leakage.
  Real-world benchmarks validate before constructing a detector. No empty dataset
  is labeled an achieved real-world evaluation.
- Timing now includes DetectionBatch construction and separates output transfer,
  class mapping and restoration. Remaining combined vendor stages are labeled.
  GPU execution remains unavailable; no asynchronous host-call timing is sold as
  GPU performance. Native/ONNX parity was rerun on actual models after the adapter changes.
- Replay result age uses the mapped monotonic deadline. A deliberately offset media
  timestamp regression test verifies this; offline timings do not masquerade as age.
- Research/product licensing are separated. No legal approval or proprietary
  permission is inferred from having downloaded a checkpoint.

## Remaining findings

**CRITICAL:** no confirmed unresolved implementation finding in the reviewed paths.
This is a bounded review, not a guarantee of absence of defects.

**HIGH — qualification evidence missing:** dataset acquisition, independently reviewed
walking annotations, real scenario slices and sustained representative video remain
open. Affected: final qualification report and model-selection decision. Consequence:
no evidence-backed Task007 primary/fallback selection. Fix: acquire suitable permitted
media, review exhaustive P0 annotations, separate calibration/test sequences, and run
the same protocol plus multi-minute replay. Unit tests do not close this gate.

**HIGH — licensing decision unresolved:** YOLO research use and proprietary distribution
need review under the actual project/distribution assumptions; RT-DETR notices and
bundled dependencies also need review. Affected: `DETECTOR_LICENSING.md`. No blanket
research exemption is claimed. Fix: document the applicable compliance route before
shipping or treating proprietary use as cleared.

**MEDIUM:** laptop power/thermal/background scheduling is not controlled; thread limits
alone do not explain latency variation. Process/frequency observations under a sandbox
are limited to what it exposes. Dataset validation cannot establish annotation semantics
or detect all near duplicates. RT-DETR processor timing remains aggregated. Optional
model dependency vulnerability review and the existing development-only npm advisory
exception remain open. See `docs/security.md`.

**LOW:** pinned vendor extension points require maintenance and repeated real-model
parity on upgrades. The strict new multi-sequence manifest and old single-frame
interchange schema have distinct purposes, documented explicitly.

No tracking, depth, segmentation, optical flow, risk/attention engine or Android work
was started. Source media/weights are ignored; no user video was uploaded. Runtime
and report code remain in the optional lab; web/API/core do not import model libraries.

## Final executed verification � 2026-10-16

`npm run verify` passed with exit 0: 358 tests (core 189, lab 142, web 24, API 3), static checks, builds, security policy and production smoke tests. `pip check` passed. Security policy retains the documented development-only advisory exception. Real-world evidence gates remain open independently of software check success.
