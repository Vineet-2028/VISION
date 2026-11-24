# Field harness implementation checkpoint

Date: 2026-10-27. This is a progress record, not a completion report.

This historical checkpoint predates the frozen Alpha engine, field worker,
local speech receiver and review UI. For the November release evidence see
the [engine release](../releases/VISION_CONTROLLED_ALPHA_V1.md) and
[field guide](../releases/VISION_ALPHA_V1_FIELD_GUIDE.md).

The rescue profile and its evidence remain frozen. No model, cadence, risk,
attention or alert-expiry threshold was retuned for this milestone.

Implemented in this continuation:

- Authenticated bounded HTTP transport and strict versioned binary frame parsing.
- Clock exchange, uncertainty, replay rejection, recording limits and session cleanup.
- Structured ZIP session exports without image/audio content.
- Dashboard age advancement during stalled requests and HTTPS requirement for LAN.
- Android CameraX capture, one replaceable pending frame, local transport and lifecycle cleanup.
- Local-voice-only TTS adapter with submission/start expiry checks; integration pending.
- A review gate page that does not fabricate review completion.

Executed verification: 22 protocol/session/gateway pytest tests passed, including
real loopback HTTP checks. Ruff and strict mypy passed for the new gateway and its
imported state/export modules before the final clock-source substitution.
Android Gradle configuration passed. Official SDK platform 36 and build tools
were installed locally. APK/lint/test and web checks are being resolved separately;
do not infer their success from SDK installation or source code presence.

Still required:

1. Connect the isolated desktop inference worker with explicit live-camera provenance
   and capture-time-preserving admission; verify model hashes and unchanged settings.
2. Connect actual alerts to phone TTS and return submission/start/completion/error
   timing events, including session/source identity and output route observations.
3. Finish actual live overlays and the existing 30-window human review interface.
4. Complete APK, Android unit/lint, web build/browser QA, full regression and
   controlled latency/backpressure/expiry tests. Recheck frozen evidence hashes.
5. Complete required milestone documentation, adversarial audit and final A–AP report.
6. Test physical Android camera, audio routing and Bluetooth with actual hardware.

V0_DEMO_AND_FIELD_TEST_HARNESS_COMPLETE: NO

Physical validation, human usefulness and production safety: NOT VALIDATED.
