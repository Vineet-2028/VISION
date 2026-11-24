# Codebase health review — 16 November 2026

## Changes

- `tools/lab.mjs` shares one 76-file tool list across formatting and lint commands. An executable comparison confirmed that the resulting command arrays exactly match the original arrays.
- Android `FrameEncoder` owns JPEG compression and bitmap recycling. `MainActivity` retains ownership of the camera image and closes it in its existing finally block. Failed compression is now explicitly rejected. Encoding quality and transport size limits are preserved.

## Verified software baseline

The local verification logs are in `benchmark-results/health-*.log`.
Guardian passed 195 tests. Python passed formatting, lint, type analysis and
1,354 tests. Web passed lint, type analysis, 42 tests and production build.
Backend verification, npm advisory checks and production HTTP smoke passed.
After the encoding extraction, Android debug assembly, JVM unit tests and
lint passed in 3 minutes 39 seconds using the existing offline dependencies.
Python network/filesystem checks and the web build needed execution outside
the restricted sandbox after permission errors.

## Design observations

Guardian production source has no Spring, Android or JavaFX imports in the
performed scan. The API owns HTTP health endpoints. Web replay parsing,
filesystem access and Lab authentication live in separate modules. Android
already separates transport, speech, sensors, pairing, encryption and history.
The activity still owns substantial session coordination and Compose UI, so
further extraction should be accompanied by lifecycle and device tests.
These observations do not constitute an exhaustive proof of SOLID compliance.

## Reproducibility and remaining acceptance

The working checkout contains substantial pre-existing uncommitted work.
Of the 76 scripts explicitly referenced by the Python check runner, 55 are
untracked. Local success therefore cannot establish fresh-clone success.
Review and include the required historical source, tests and configuration
before tagging a release, then verify the resulting clean checkout.

Physical camera, Bluetooth, backgrounding and connection-loss acceptance
still require the target phone. Automated software checks cannot establish
that a person heard or understood an alert.
