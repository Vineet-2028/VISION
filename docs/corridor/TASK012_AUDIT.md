# Task012 adversarial audit

## Read-only pre-task pass

Inspected WorldState/entity/surface/camera contracts, ages/capabilities, Guardian geometry/transforms/timing, track/depth/motion/surface joins, scheduler/recording, replacement/integration docs and existing tests. Confirmed one state timestamp, explicit evidence age/status, relative-versus-metric separation, source-supported world points, UNVERIFIED semantics and no existing safety decisions. Found missing independent image metadata and spatially localized compact surface evidence; resolved with additive optional contracts, not vendor coupling or subsystem rewrites.

The initial `npm run verify` reached 252 passing perception tests but 90 fixture setup errors because sandbox access to pytest temporary directories failed. It is not recorded as a passed baseline. The subsequent retry encountered the new Java source's formatting/compatibility errors during development. These were corrected; final verification evidence is in the result report. Guardian deliberately targets Java 8 despite running on JDK21.

## Implementation audit

CRITICAL: no outstanding identified implementation defect. Unknown space remains explicit; draft labels cannot become ground truth; no safe-path/hazard/collision vocabulary is emitted as a decision. WorldState is never mutated and outside entities remain present. Wrong source/frame/time, invalid pose and relative depth cannot establish metric geometry.

HIGH: no outstanding identified implementation defect after fixes. Added exact-frame surface alignment (old masks cannot silently follow a turning camera), explicit image metadata, source validation, finite/unit pose validation and a current calibrated-point gate. Translated Guardian's invalid-plane Java exception at the typed bridge so degenerate inputs fall back instead of terminating the pipeline; three regression cases cover this. Reused Guardian metric math and process JVM. Realtime creates no additional queue. Point samples avoid copying dense masks or claiming bbox area as semantic coverage. No model-specific adapter imports enter the analyzer.

MEDIUM: camera-forward is an imperfect body-direction proxy; image geometry and sparse semantic samples are research heuristics; depth/physical motion/semantic accuracy remain unvalidated; identity fragmentation and upstream throughput remain inherited limitations. Near-plane-crossing polygons conservatively lose image projection. Strong distortion needs a richer projected-edge representation. Independent scenario coverage and human semantic ground truth remain incomplete.

LOW: future richer footprint and exact surface-region representations may improve diagnostics. No premature grid/map/person profile framework was added.

Privacy/security: local-only and opt-in debug PNG/JSON; no new network endpoints, credentials, telemetry, biometrics or dependencies. Existing five reviewed development advisory entries remain subject to the repository security gate. No production-security or safety certification is implied.
