# Task 005 adversarial audit

The initial audit was read-only. Existing core frame conventions, camera geometry,
calibration versions, monotonic time, pose synchronization, Java 8 target and
test-only dependencies were preserved. Web/API boundaries were inspected; no
perception code was added there.

After implementation, a separate read-only review inspected all lab source, root
integration, CI, docs and existing boundaries before the corrections below.

## CRITICAL

No unresolved critical finding identified. The review is not a proof of absence.

## HIGH — corrected

- `pipeline.py`: freshness was checked only before preprocessing. A slow component
  could publish an expired result. Added cancellation/freshness guards after
  preprocessing, before each component and before publication; controlled-clock
  regressions require stale results to be dropped.
- `pipeline.py`, `recording.py`: source iterator setup happened before the protected
  lifecycle; iterator close and metrics finalization failures could leave misleading
  success status. All setup/cleanup paths now finalize source/renderer/recorder and
  propagate failure. Regression tests inject iterator open/close, recorder, source,
  component, scheduler, preprocessing and listener errors.

## MEDIUM — small corrections

- `clocks.py`, `sources.py`, `pipeline.py`: the CLI dry run exposed coarse tick-count
  resolution from Python 3.12 Windows `monotonic_ns`. All processing stages now use
  the same high-resolution monotonic `perf_counter_ns`; its resolution is exported.
  Media observation timestamps remain untouched.

- `pipeline.py`: callback exceptions during acceptance/completion could double-count
  a frame or abandon uncounted queue entries. Ownership transfer and terminal accounting
  now precede callbacks; cleanup accounts each retained frame even if a callback fails.
- `pipeline.py`, `metrics.py`: viewer FPS requested every percentile distribution on
  each frame. Dedicated constant-work FPS accessors avoid repeated sorting.
- `recording.py`: headless non-recording runs serialized unused event/result dictionaries.
  Serialization is now conditional on an open recording stream.

## LOW / residual limitations

- `geometry.py`: JPype uses dynamic foreign objects inside a narrow typed wrapper.
  Core integration tests exercise its actual JAR. Python and JVM architectures must match.
- `sources.py`: native decoder work is not preemptible within a call and frame-size
  checks cannot sandbox native codec allocation. Supported local media only; use a
  future resource-limited decoder process before accepting hostile files as a service.
- Optional Tk requires a display/Tk installation. Headless CI does not validate native
  GUI appearance. Renderer contract/cleanup is tested with a fake adapter.
- Native wheel licensing, mobile/device performance and real camera calibration are
  deployment/R&D work, not validated by synthetic fixtures.
- Existing web lint dependency advisory exception remains documented in `docs/security.md`.
  No claim of a vulnerability-free dependency tree is made.

Every subprocess runner propagates nonzero exit; CI does not use continue-on-error.
No webcam, model, display, remote data or telemetry is required by tests. Replay
opens file handles rather than interpolating media paths into shells. Exported
artifacts omit operational paths, exception strings, usernames and calibration
free text. User-supplied IDs and opt-in images still require privacy review.
