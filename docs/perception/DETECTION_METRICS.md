# Detection metrics

Implemented diagnostics use class-aware greedy matching in descending confidence order. Equal confidence retains input order; equal IoU uses annotation order. Each regular ground truth can match once. Threshold comparisons are inclusive. Matching prefers regular truth over ignored regions. Non-crowd ignored truth absorbs one prediction; crowd regions absorb multiple using intersection over prediction area. Ignored/crowd truth does not enter recall denominators.

Report TP, FP, FN, precision, recall, F1 and FP per 100 evaluated images. Empty precision/recall denominators produce null, not perfect performance. Every candidate uses the same manifest, ordering, class scope and thresholds. Missing annotations cannot be treated as negative examples. Failed inference fails a run and never supplies an empty successful prediction.

The runner evaluates IoU 0.50 and 0.75, with confidence 0.05, 0.10, 0.20, 0.25, 0.40, 0.60, 0.80 and 0.90. It reports P0 micro recall, each class denominator/recall, localization errors, and false-positive/negative references. Micro recall is frequency-weighted; always inspect minority-class counts. This is not official COCO AP/mAP.

Size is box area divided by original image area: TINY <0.001; SMALL [0.001,0.01); MEDIUM [0.01,0.1); LARGE >=0.1. Boundaries are configurable in the metric function. This is an image-size proxy, not metric distance. Size recall uses matches from the full evaluation, rather than rematching size-filtered detections.

Center and bottom-center Euclidean errors normalize horizontal displacement by image width and vertical displacement by image height. Means apply only to matched detections; misses remain visible separately. They are not ground-plane localization or depth errors.

COCO does not supply reliable per-instance occlusion/truncation or walking-scene labels. These remain unknown. Attribute aggregates retain UNKNOWN separately. A density proxy splits frames at five non-ignored annotated people; it is not a verified crowd-scene label. Error review includes low-IoU matches and nearest-ground-truth context for false positives, distinguishing possible class confusion from duplicates. This is diagnostic association, not a complete confusion matrix. Do not infer low light, motion blur, camera motion or distance from class membership. Official AP and verified real scenario slices remain follow-up work.
