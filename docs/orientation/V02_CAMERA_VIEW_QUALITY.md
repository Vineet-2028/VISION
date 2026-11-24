# V0.2 deterministic camera diagnostics

`CameraViewQualityEstimator` samples at most 128 × 128 pixels by default. It computes luminance, exposure fractions, entropy, spatial detail, and directional texture. `ViewQualityConfig` is immutable, strict, finite-valued, versioned, and hashed into every result. Sample dimensions and thresholds are configurable and bounded.

Results preserve the source frame identity and contain GOOD, DEGRADED, UNUSABLE, or UNKNOWN. Near-total dark/bright clipping produces UNUSABLE. Uniformity or low detail produces DEGRADED. Tiny images and RGBA without an alpha-compositing policy produce UNKNOWN. UNKNOWN and UNUSABLE do not permit scene reasoning through the result's explicit capability property.

Uniformity is only an occlusion-like indicator: a wall and a covered lens may look similar. Low spatial detail does not prove blur. Directional texture does not prove motion smear. Brightness does not establish that the camera faces the sky. No unsupported physical cause or safety status is fabricated. GOOD means the implemented diagnostics found no configured problem; it does not certify visibility or correct detections.

Nine generated-image tests cover exposure, uniformity, low detail, RGB/BGR agreement, bounded sampling, unsupported formats, configuration validation, and directional patterns. These fixtures are not human-reviewed real-world quality labels.

Run the full-file diagnostic probe from the repository root:

```powershell
& apps/perception-lab/.venv/Scripts/python.exe tools/v02_view_probe.py --video 'datasets/sentinel_first_person_v1/raw/Screen Recording 2026-10-16 223504.mp4' --output benchmark-results/v02/view-probe-new
```

It streams the entire local file and samples at one-second source-time intervals. It writes no images or audio, only diagnostics with video/configuration hashes. Output directories are exclusive, preserving prior runs. Timing covers diagnostics only, excluding decoding and file writes. The bounded latency histogram has 1 µs bins and reports overflow above 100 ms explicitly. A failed/empty decode cannot count as a clean probe.

Runtime capability gating is implemented behind `camera_view_health`. UNUSABLE or
UNKNOWN views skip inference, publish unavailable scene/capability state and reset
pending attention/alerts. Synthetic tests verify suppression and recovery. The
November 5 candidate profile enables this policy for realtime measurement; starting
that run is not proof that the qualification passed.

Pending: labeled usability accuracy, comparison under blur/roll/occlusion, final
realtime qualification, temporal ground/sky evidence, and measured need for any
learned quality classifier. The standalone diagnostic probe does not satisfy the
full perception pipeline replay requirement.
