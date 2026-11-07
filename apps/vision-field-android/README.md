# VISION field harness

Native Kotlin/Compose/CameraX engineering client. This is separate from the
original Task019 on-device inference roadmap. Inference remains on the desktop.

The harness sends bounded camera captures and timestamped sensor samples to the
desktop gateway, polls for fresh scene results and submits authorized alerts to
local TTS. Software checks and physical-device validation are separate. Use the
harness only for supervised engineering tests.

## Build from the repository root (PowerShell)

Use JDK 21. Install Android SDK platform 36 and build tools. Set `ANDROID_HOME`
to the installed SDK or put `sdk.dir` in this app's ignored `local.properties`.

```powershell
Push-Location apps/vision-field-android
.\gradlew.bat :app:assembleDebug :app:testDebugUnitTest :app:lintDebug --no-daemon
Pop-Location
```

APK: `app/build/outputs/apk/debug/app-debug.apk`. This is a debug engineering
artifact, not a signed production release.

For a OneDrive checkout, redirect generated files to a dedicated local directory
if Gradle cannot replace read-only test results. From the Android project run
`.\gradlew.bat :app:assembleDebug :app:testDebugUnitTest :app:lintDebug "-PfieldBuildDirectory=$env:LOCALAPPDATA\VISION\field-build" --no-daemon`.
The APK is then under `outputs/apk/debug/` in that directory.

For wireless setup, open the [same-LAN field guide](../../docs/releases/VISION_WIRELESS_ALPHA_FIELD_GUIDE.md).
Pair PC opens the QR scanner. The ephemeral token field applies to the legacy USB workflow.

To use the legacy USB connection, configure forwarding with the inference gateway running:

```powershell
adb reverse tcp:8765 tcp:8765
adb install -r apps/vision-field-android/app/build/outputs/apk/debug/app-debug.apk
```

Use `http://127.0.0.1:8765` with USB forwarding and the ephemeral gateway token.
Private LAN connections require trusted HTTPS. The client never installs a
trust-all certificate manager or disables hostname validation.

The camera must expose Android's REALTIME timestamp source. Unsupported clocks
fail closed. Stop, backgrounding, rotation/recreation and disconnect end capture.
No raw camera files, token preferences, analytics or cloud backups are stored.
Audio follows Android's normal output routing; Bluetooth delivery requires a
physical device test. TTS callback start is not proof that a person heard sound.

Pinned versions are in the Gradle files. Lint fails on code, compatibility and
security warnings. Only newer-version notification checks are excluded, because
remote releases must not change the outcome of an otherwise identical build.
Dependency updates and vulnerabilities still require a separate review.
