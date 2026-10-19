# Model selection

No detector is production-qualified from published COCO scores or a small still-image subset.

## Current Task006C local research selection — 2026-10-18

Primary: **PicoDet-S416 ONNX, CPU FP32, one thread, score .25**.
Fallback: **YOLOX-Nano416 ONNX, CPU FP32, one thread, score .15**.
These are frozen CALIBRATION settings, not TEST-tuned choices. On 161 held-out
frames, PicoDet matched 3,706/4,935 labeled objects with one false positive; YOLOX
matched 1,966/4,935 with 260 false positives. The labels are user-reviewed model
proposals, so agreement can favor proposal generators; this is not an independent
accuracy ranking. No deployment approval is implied by near-perfect measured precision.

PicoDet is the provisional accuracy-oriented research choice; YOLOX provides a
different compact implementation and CPU cadence alternative. Both need missing
detection/gap handling downstream. PicoDet's prior sustained run achieved only
2.43 detector Hz against 5 Hz requested. No hard real-time or mobile guarantee.
Commercial checkpoint rights remain under review. Ultralytics alternatives remain
research references, not a structural dependency.

Pretrained outputs are sufficient for local Task007 tracking engineering; no
fine-tuning is justified on this correlated, model-assisted dataset. Improving
from V1 TEST errors requires new untouched evaluation data. See the
[reviewed qualification report](../research/results/task006c-reviewed-2026-10-18.md)
for all candidates, denominators, limitations and final verification. Earlier
decisions below are historical. No Task007 code was implemented in this task.

Research candidates are YOLO26n, YOLO26s, YOLO11n and official RT-DETRv2-R18. The comparison should examine P0 and minority-class recall, tiny/small recall, false positives, matched bottom-center localization, measured tail latency, export behavior and licensing.

SelectionPolicy has explicit minimum recall, maximum P95 latency and maximum FP/100 gates; export verification and license approval are mandatory. No production thresholds are invented by the implementation. Missing evidence must prevent constructing an approved candidate. pareto_front only identifies accuracy/latency non-dominance; it is not a safety or licensing approval. Filter by gates before selecting a deployable candidate.

Historical Task006 diagnostic candidate (not a current Task007 selection): **YOLO26s, 640, FP32**. Historical compact fallback:
**YOLO26n, 640, FP32**. These are candidates for further evaluation, not winners of
the production acceptance policy. At confidence 0.25/IoU 0.50 the primary recalled
71.70% of P0 objects and 37.50% of tiny objects, versus 60.85% and 20.83% for the
fallback. Both native and CPU ONNX outputs passed detection parity on all 36 images.
Runtime choice remains open because repeat laptop latency changed substantially.

RT-DETRv2-R18 reached 88.68% recall at that threshold, but 1008.33 FP/100 images and
much higher CPU latency. Higher thresholds improve its FP tradeoff; retain it as
the Apache-2.0 architecture alternative. YOLO11n remains the mature baseline.
All four models exported and passed native/ONNX parity. None has target-mobile
validation or production license approval. No candidate is approved by the hard gates.

See the [dated measurements](../research/results/detector-benchmark-2026-10-14.md)
and machine-readable matrix for threshold curves, denominators, repeatability and
synthetic stress results. Verified real walking, low-light and occlusion validation
remains open. Do not begin Task007 based solely on successful unit tests.

## Task 006B decision

**Task007 PRIMARY: NOT SELECTED. FALLBACK: NOT SELECTED.**
Matched-FP analysis supersedes the fixed-0.25 ranking as comparative evidence.
At a 50 FP/100 cap the public subset favors YOLO26s recall, while RT-DETR improves
recall at the 100 FP/100 cap. Neither conclusion is representative walking evidence.
The laptop CPU path is not established at the requested 5�15 Hz. Real-world,
localization, freshness and permission gates remain open. Do not automatically
preserve the historical primary or remove alternative implementations before the
qualification evidence exists. See the [Task006B report](../research/results/detector-qualification-2026-10-15.md).

## Task006C research gate (2026-10-17)

Completion means provisional engineering qualification for Task007, not production
safety certification. Android, GPU, final thresholds and enterprise licenses are not
required. User-owned first-person footage replaces permission-gated datasets.
Ultralytics remains RESEARCH_REFERENCE. RT-DETR and practical permissive candidates
require calibration-only operating points and held-out reviewed qualification before
primary/fallback selection. Do not train before pretrained qualification demonstrates
a concrete need. See ../../datasets/sentinel_first_person_v1/README.md and the
Task001�006 integration audit.
