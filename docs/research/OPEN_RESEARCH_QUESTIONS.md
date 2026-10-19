# Open research questions

All unanswered. Priorities describe research dependencies, not implemented risk
levels. Link answers to reproducible experiment IDs; do not close with conjecture.

## P0

1. Which detector achieves the best hazard recall/latency tradeoff?
2. Can monocular depth provide sufficiently stable relative distance?
3. How accurately can camera + IMU remove ego-motion?
4. What false-alert rate becomes annoying to users?
5. What warning lead time is useful but not excessively early?
6. How should track uncertainty propagate into TTC/CPA?
7. How do we detect ground-level hazards, including holes and descending steps?
8. How should Guardian communicate degraded perception?
9. Which computations need 30 Hz and which can run slower?
10. What device temperatures cause sustained throttling?
11. What clock synchronization and calibration uncertainty makes motion unusable?
12. What datasets and supervised blind-user studies can ethically validate usefulness?

## P1

- How long can tracks remain useful through occlusion without false confidence?
- Which filtering models provide acceptable noise/lag tradeoffs?
- When do turning/accelerating trajectories invalidate constant-velocity CPA?
- How should device heading be mapped to body-referenced directional presentation?
- Which per-device runtime fallback provides sustained offline performance?
- How can degraded states recover without sudden contradictory output?
- Which calibration, crop and rolling-shutter models are necessary per camera?

## P2

- Is appearance re-identification worth its privacy, memory and latency costs?
- Which personalization preferences remain understandable across contexts?
- What future stereo/depth hardware materially improves adverse-scene coverage?
- Which optional cloud/explore features are useful without entering the critical loop?

## Camera geometry follow-up (Task 003)

- P0: Which per-mode calibration identities cover lens/focus/zoom/OIS/EIS changes?
- P0: What validated pixel, intrinsic, extrinsic, pose and ground uncertainty model
  can accompany nominal rays and reject unstable near-horizon intersections?
- P0: How will capture-time pose/ground interpolation account for synchronization
  error and rolling shutter without relabeling stale samples?
- P0: Which lens families and calibrated domains are required by actual hardware?
- P1: What checkerboard/ChArUco coverage and held-out protocol establish repeatability?
- P1: What exact integer resize and asymmetric padding does each adapter perform?
- P1: Does horizon reasoning need a clipped ideal line or a distorted sampled curve?
- P2: When do ray maps or distortion grids improve sustained throughput enough to
  justify memory, interpolation error and calibration invalidation complexity?

Track evidence in RND-CAM-001 through RND-CAM-008; all remain planned.

## Task 004 temporal follow-up

- P0: What are the actual shared-timebase, offset, drift and exposure-midpoint errors per device/mode?
- P0: What covariance and bias models justify interpolation, propagation and derivative confidence?
- P0: How should future runtime reset every dependent history atomically after discontinuities?
- P1: Which orientation source, stationary policies and filter cutoffs meet measured error/lag budgets?
- P1: When should CV/CA prediction remain unavailable because source acceleration is unreliable?
- P1: Can complementary fusion or a future ESKF improve on adapter orientation without hiding drift?
- P2: Would ring-buffer insertion materially improve measured 200 Hz performance over the bounded sorted buffer?

Evidence belongs in RND-IMU-001..012 and RND-MOTION-001..003. All are PLANNED.

## Task006C evidence update (2026-10-18)

User review and the confirmed shelter correction are imported and validated.
Calibration settings for all six viable candidates are frozen. See the reviewed
qualification report for the current decision. Independent annotation quality,
scenario-specific robustness, target-device timing and production safety remain open.
Future optimization using V1 test errors requires a new untouched evaluation version.

## Historical Task006C evidence gates (2026-10-17, superseded)

- HUMAN_REVIEW_REQUIRED: 458 local first-person frames have draft ensemble proposals.
- NOT AVAILABLE: class/scenario ground truth, frozen operating points and held-out
  qualification; no primary/fallback or pretrained sufficiency conclusion yet.
- MEASURED: one 24:58.833 recording with three temporal splits and 60-second guards.
  Correlated windows cannot establish generalization across wearers/cameras/routes.
- OPEN: sustained useful detector throughput at 5/10 Hz on this CPU, particularly
  when full-resolution decoding falls behind; bounded queues alone do not solve it.
- NOT VERIFIED: native parity for the new YOLOX/PicoDet ONNX artifacts; RTMDet's
  compatible MMCV binary was unavailable in the current Windows/Python environment.
- PLANNED: freeze CALIBRATION choices only after human review; score TEST once.
