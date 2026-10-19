# Detector research register — Task 006

These are research decisions, not production acceptance claims. Consult the dated result report for executed evidence. No missing result is treated as a pass.

## RND-DET-001 — YOLO26n versus YOLO26s

- QUESTION: Does the small model improve P0 recall enough to justify latency?
- WHY: Misses and frame freshness both matter.
- HYPOTHESIS: The larger model improves difficult-object recall.
- EXPERIMENT: Run both on identical images at 512/640/768 and identical thresholds.
- METRICS: P0/per-class/small recall; FP/100; E2E P95/P99.
- DECISION CRITERION: Prefer a non-dominated recall/latency tradeoff; inspect FP and minority classes before advancing.
- STATUS: PARTIAL � Measured on diagnostic stills at three sizes; provisional only.

## RND-DET-002 — YOLO26 versus YOLO11

- QUESTION: Does the newer architecture beat the mature nano baseline?
- WHY: Popularity is not deployment evidence.
- HYPOTHESIS: YOLO26n may improve the accuracy/latency frontier.
- EXPERIMENT: Compare pinned checkpoints with the same manifest/runtime/thresholds.
- METRICS: Recall, localization and latency; export parity.
- DECISION CRITERION: Retain YOLO11 if YOLO26 does not improve the measured tradeoff; do not select by release date.
- STATUS: PARTIAL � Measured on diagnostic stills; confidence sweeps and localization retained.

## RND-DET-003 — YOLO versus RT-DETR

- QUESTION: Does a transformer candidate improve the deployable tradeoff?
- WHY: Architecture and license diversity reduce lock-in.
- HYPOTHESIS: RT-DETR may offer competitive recall with simpler licensing.
- EXPERIMENT: Run official converted R18 at its recommended 640 input against YOLO.
- METRICS: P0 recall, FP/100, tail latency, export/license gates.
- DECISION CRITERION: Advance RT-DETR only if its recall benefit survives FP, latency, export and licensing review.
- STATUS: PARTIAL � Native CPU comparison measured; deployment decision remains open.

## RND-DET-004 — Resolution and small objects

- QUESTION: Which input resolution improves tiny-object recall?
- WHY: Distant image-space objects are often small.
- HYPOTHESIS: 768 improves recall at additional compute cost.
- EXPERIMENT: Compare 512/640/768; keep size buckets in original image coordinates.
- METRICS: Tiny/small recall denominators; P95/P99.
- DECISION CRITERION: Advance a resolution only when its tiny/small recall gain justifies measured latency; no production budget is assumed.
- STATUS: PARTIAL � Measured YOLO 512/640/768; RT-DETR kept at recommended 640.

## RND-DET-005 — Confidence operating point

- QUESTION: What recall/false-positive tradeoff does each threshold create?
- WHY: A single F1 maximum is not a safety policy.
- HYPOTHESIS: Lower thresholds improve recall but increase nuisance detections.
- EXPERIMENT: Sweep 0.01�0.95 on the 0.01-floor reruns; retain same-set calibration disclosure.
- METRICS: Precision/recall/F1, FP/100, P0 and minority-class recall.
- DECISION CRITERION: Retain the full recall/FP curve; product acceptance must specify both constraints before a production threshold is chosen.
- STATUS: PARTIAL � Eight thresholds measured at IoU 0.50/0.75; no production threshold selected.

## RND-DET-006 — Native versus ONNX

- QUESTION: Does export preserve semantics and useful performance?
- WHY: Export can alter heads, coordinate conventions or precision.
- HYPOTHESIS: Validated FP32 export should preserve detections within documented tolerance.
- EXPERIMENT: Export pinned weights, validate shapes/opset and compare identical frames.
- METRICS: Box/score/class agreement; counts; P95.
- DECISION CRITERION: Require all-frame class/count agreement, score error <=0.001 and each box-edge error <=0.5 pixels; investigate every failure.
- STATUS: MEASURED � All four candidates passed structural export and same-frame native/ONNX parity; consult dated results for exact outcomes.

## RND-DET-007 — CPU baseline

- QUESTION: Can each candidate support the desired processing cadence on CPU?
- WHY: A fallback must work without GPU availability.
- HYPOTHESIS: Nano candidates may provide the lowest CPU tail latency.
- EXPERIMENT: Batch-one warmed runs with controlled threads and full loaded-image timing.
- METRICS: Cold call, P50/P90/P95/P99, preprocessing/inference/postprocessing.
- DECISION CRITERION: Compare controlled batch-one end-to-end distributions; repeat unstable rankings before deployment decisions.
- STATUS: PARTIAL � All four candidates measured on controlled one-thread CPU; desktop variation remains a limitation.

## RND-DET-008 — GPU acceleration

- QUESTION: Does RTX3050 improve useful end-to-end performance?
- WHY: Transfer overhead and asynchronous kernels can mislead.
- HYPOTHESIS: GPU helps inference more than small preprocessing stages.
- EXPERIMENT: Record driver/runtime; synchronize boundaries; run identical images.
- METRICS: Transfer-inclusive latency, GPU peak allocated memory where measured.
- DECISION CRITERION: Compare synchronized transfer-inclusive GPU runs with CPU; unavailable execution remains unverified.
- STATUS: BLOCKED � Deferred: installed Torch is CPU-only; user declined CUDA-wheel installation.

## RND-DET-009 — FP16 precision

- QUESTION: Does half precision retain useful accuracy on supported GPU?
- WHY: Latency savings cannot hide quality regression.
- HYPOTHESIS: FP16 should reduce cost with small detection changes.
- EXPERIMENT: Compare FP32/FP16 on the same GPU and frames; no CPU half claims.
- METRICS: Prediction parity, recall, FP/100 and tail latency.
- DECISION CRITERION: Require acceptable FP32/FP16 detection parity and measured latency improvement on supported hardware.
- STATUS: BLOCKED � Deferred with GPU runtime; CPU FP16 is not claimed.

## RND-DET-010 — Low light

- QUESTION: How does real low light affect recall?
- WHY: Dark scenes are part of the intended environment.
- HYPOTHESIS: Low contrast will reduce recall, especially for small objects.
- EXPERIMENT: Curate labeled real low-light media; report synthetic darkening separately.
- METRICS: Per-class/size recall and false positives.
- DECISION CRITERION: A synthetic stress result can motivate research but cannot close the real low-light requirement.
- STATUS: PARTIAL � Synthetic 25% brightness experiment executed; verified real low-light slice remains open.

## RND-DET-011 — Blur

- QUESTION: How do real and controlled motion blur affect detection?
- WHY: Camera motion and object motion degrade edges.
- HYPOTHESIS: Tiny objects are disproportionately affected.
- EXPERIMENT: Use labeled real blur plus explicitly parameterized synthetic stress images.
- METRICS: Recall by blur source/severity and object size.
- DECISION CRITERION: Keep synthetic blur separate; real camera-motion robustness requires annotated video evidence.
- STATUS: PARTIAL � Synthetic nine-pixel horizontal blur experiment executed; real blur/video remains open.

## RND-DET-012 — Occlusion

- QUESTION: Which classes fail under verified partial occlusion?
- WHY: Missing partially visible people is consequential.
- HYPOTHESIS: Heavier occlusion reduces recall.
- EXPERIMENT: Human-review occlusion labels; never treat COCO crowd as equivalent to occlusion.
- METRICS: Occluded recall with counts and unknown-label coverage.
- DECISION CRITERION: Require verified visibility labels and nonempty denominators; UNKNOWN cannot pass this experiment.
- STATUS: PARTIAL � Open: acquired annotations have no verified occlusion labels.

## RND-DET-013 — Crowding

- QUESTION: Does crowded imagery cause suppression or query-limit misses?
- WHY: Dense scenes can exceed postprocessing capacity.
- HYPOTHESIS: Suppression and max-detection limits affect dense frames.
- EXPERIMENT: Compare annotated density slices and separately handle crowd ignore regions.
- METRICS: Recall/counts, duplicates, max-detection saturation.
- DECISION CRITERION: Report density-proxy recall separately; verified crowd evaluation must include duplicates and latency.
- STATUS: PARTIAL � Annotated-person-density proxy calculated; actual crowd-scene validation remains open.

## RND-DET-014 — Bottom-center localization

- QUESTION: Are matched box bottoms stable enough for downstream geometry?
- WHY: Ground-contact hypotheses depend on localization, not only class confidence.
- HYPOTHESIS: Larger models may improve box-bottom precision.
- EXPERIMENT: Measure normalized bottom-center error only for matched pairs and report misses.
- METRICS: Mean/distribution bottom error, center error, matched IoU.
- DECISION CRITERION: Compare matched localization alongside misses and stricter IoU; low error on a few easy matches is insufficient.
- STATUS: PARTIAL � Measured matched center/bottom-center errors and IoU; no ground-plane accuracy claim.

## RND-DET-015 — Desktop to mobile

- QUESTION: Which desktop result is a plausible mobile candidate?
- WHY: Desktop latency cannot substitute for target-device measurements.
- HYPOTHESIS: Compact exported models may transfer better, but ranking may change.
- EXPERIMENT: Validate operator support now; later benchmark actual mobile hardware.
- METRICS: Export compatibility, artifact size; mobile results remain unmeasured.
- DECISION CRITERION: Only actual target-device measurements can establish mobile latency and memory feasibility.
- STATUS: PARTIAL � Open: no target mobile benchmark; desktop results are hypotheses only.

## RND-DET-016 — Licensing feasibility

- QUESTION: Which candidates can legally support Sentinel's intended distribution?
- WHY: A performant model can still fail deployment constraints.
- HYPOTHESIS: Permissive RT-DETR terms may simplify proprietary distribution.
- EXPERIMENT: Review exact code/checkpoint/dependency terms and obtain legal sign-off.
- METRICS: License gate, notices, redistribution conditions, unresolved obligations.
- DECISION CRITERION: No production approval without exact artifact/dependency terms, required notices and distribution-specific review.
- STATUS: BLOCKED � Source/checkpoint terms documented; no production legal approval.

## Task 006B evidence update � 2026-10-15

Dense public PR curves, matched FP/precision/recall points, annotation validation,
replay-clock age metrics and new native/ONNX parity are implemented and tested.
RND-DET-005 remains PARTIAL because no independent real-world calibration/test
experiment exists. RND-DET-006 MEASURED applies to CPU FP32 static export only.
Real walking/low-light/blur/occlusion, representative sustained video and final
selection remain BLOCKED on suitable permitted, reviewed media. No training is
authorized or justified by this small diagnostic subset.
