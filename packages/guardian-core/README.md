# Guardian core

Pure Java mathematical and observation contracts. No runtime dependencies, Spring
parent, network, persistence, telemetry, mutable globals, sensors, inference, tracking,
or risk policy. This JAR is not an active Guardian runtime.

Production and test source compile with `--release 8` on JDK 21. This restricts
language, bytecode, and standard-library APIs; Android packaging/desugaring still
needs validation when mobile is restored. JUnit 5.12.2 is test-only. The module
uses the existing repository Maven wrapper without inheriting the API's POM.

```powershell
npm run format:core
npm run check:core
npm run verify
```

`check:core` runs a clean compile, Spotless, compiler lint with warnings as errors,
JUnit with no-tests failure, JAR packaging, and SpotBugs. Root verification and
backend CI invoke it unconditionally. Output: `target/guardian-core-0.1.0.jar`.

Read [mathematical contracts](../../docs/guardian-core.md), the
[mobile ADR](../../docs/adr/0002-on-device-guardian.md), and
[research roadmap](../../docs/research/GUARDIAN_RND_ROADMAP.md).

Task 003 adds calibration-driven camera/image geometry and nominal world rays and
ground intersections. Read the [camera model](../../docs/geometry/CAMERA_MODEL.md)
and [calibration schema](../../docs/calibration/CALIBRATION_SCHEMA.md) before using
these contracts. No real device calibration or safety accuracy is established.

Task 004 provides [time synchronization](../../docs/motion/TIME_SYNCHRONIZATION.md),
[IMU math](../../docs/motion/IMU_MODEL.md), filtering and motion foundations.
Stateful instances are single-owner, with explicit reset and consumer-provided
limits; this is not complete sensor fusion or drift-free navigation.
