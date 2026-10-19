# Offline calibration tooling plan

Status: PLANNED. No device calibration or accuracy measurement has been performed.
A future offline tool may use OpenCV in an isolated tooling environment, never as
a guardian-core runtime dependency. It exports the versioned calibration schema.

1. Record camera/lens identity, exact capture resolution, pixel convention, crop,
   zoom, focus, OIS/EIS state and timestamp behavior. Disable automatic geometry
   changes where possible; otherwise characterize them per capture mode.
2. Compare a measured checkerboard with a ChArUco target. Measure printed geometry
   and planarity. ChArUco IDs can support partial views; neither target guarantees
   corner quality under blur or glare. Preserve raw local evidence with consent.
3. Collect varied orientations and distances covering center, edges and corners.
   Determine view count experimentally through convergence and repeatability;
   do not declare an arbitrary number sufficient. Split fit and held-out views.
4. Reject poor corners using documented blur, saturation, visibility and fit checks.
   Log exclusion reasons and counts so rejection cannot hide failures. Evaluate
   low light, motion blur, focus changes, temperature, OIS and EIS separately.
5. Compare no-distortion, Brown-Conrady and appropriate alternative lens families
   on held-out reprojection residual distributions and spatial residual maps.
   Reject unsupported models in the production adapter. Certify the Brown domain.
6. Repeat independent sessions. Report RMS, per-view and per-region errors, sample
   counts, coverage, repeatability and confidence intervals. Low training RMS alone
   is insufficient and must not become an invented safety threshold.
7. Measure CAMERA->DEVICE extrinsics against a physical reference with nonzero
   translation/rotation; validate composition and timing. Intrinsics do not supply
   extrinsics. Export identities, versions and evidence without fabricated fields.
8. Validate exported geometry against held-out bearings and surveyed ground points,
   including horizon/tilt sensitivity. Test exact resize/crop/rotation pipelines.
   Human review and application-specific acceptance criteria precede device use.

Research references: [OpenCV calibration](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html)
and [ChArUco calibration](https://docs.opencv.org/4.13.0/da/d13/tutorial_aruco_calibration.html).
These guide the planned tool; no calibration result is claimed.
