# Reviewed-data evaluation protocol

Declared before qualification inference. Dataset manifest SHA256:
`5aaffcd6ec428805e90404633b32d0f340f63ba1a34c8d0a075ba8f5a9275b21`.
User-reviewed flags are retained; one user-confirmed TRAIN→SHELTER correction is
recorded separately. Scenario labels are UNKNOWN. Model-assisted annotation bias
and single-recording correlation remain limitations, not measured generalization.

All six installed viable candidates run CALIBRATION (115 frames), followed by a
frozen operating-point artifact, before any TEST inference (161 frames). TRAIN_DEV
is excluded. RTMDet remains unavailable in this environment. YOLO26n/26s/11n and
RT-DETRv2-R18 use their established 640 input; YOLOX-Nano/PicoDet use their official
fixed 416 exports. All use CPU FP32, batch1, one model thread, five warmups and score
floor .03. This is comparison of declared candidate configurations, not equal-input
architecture isolation. No input-resolution search will use TEST results.

The confidence grid and matched policies are predefined by the qualification tool:
FP/100 frames 25/50/100; precision .8/.9/.95; recall .8/.85/.9/.95. Freeze every
available point using CALIBRATION only. Report unavailable targets honestly.
Use the frozen **100 FP/100-frame calibration budget** as the main cross-candidate
operating point; show the other policies as sensitivity analyses, not alternatives
chosen after TEST. Qualification FP burden is measured and may exceed that budget.

Research selection follows the user's ordering: qualification P0 recall and false
positives, pedestrian/two-wheeler/vehicle recall, small-object and localization
quality, sustained timing, size/export practicality and licensing. Accuracy wins
do not override unusable latency or unresolved product licensing. YOLO results
remain research references. No candidate becomes safety validated by this protocol.

SHELTER is annotation-only context, excluded from P0 truth; predicted P0 objects
over a shelter remain ordinary false positives. No new learned detector class is
claimed. No training is justified merely to reproduce systematic annotation errors.
Training requires trustworthy error evidence, sufficient TRAIN_DEV labels and an
untouched future qualification version if development uses this TEST evidence.

Runtime results from the previous pass remain separate evidence. Full repository
verification will be rerun after any code fixes; no Task007 implementation occurs.
