# Local field session

Use a stationary supervised setup. Stop if camera identity, time synchronization,
transport or view quality becomes unavailable. Keep the browser dashboard off the
alert delivery path.

From the repository root, launch the local gateway in one PowerShell terminal:

```powershell
.\apps\perception-lab\.venv\Scripts\python.exe tools/alpha_field_gateway.py --manifest benchmark-results/v02/VISION_CONTROLLED_ALPHA_V1/manifest.json --ort-runtime benchmark-results/v0-rescue/gpu-runtime --cuda-libraries benchmark-results/v0-rescue/gpu-libraries --cudnn-directory benchmark-results/v0-rescue/cudnn-9.10/nvidia/cudnn/bin
```

The gateway checks the frozen engine and model hashes. It prints a fresh pairing
token in this terminal. Keep the token in the local session. USB forwarding uses
the default loopback binding. A private LAN binding requires an explicit trusted
TLS certificate and key.

```powershell
.\.tools\android-sdk\platform-tools\adb.exe devices
.\.tools\android-sdk\platform-tools\adb.exe reverse tcp:8765 tcp:8765
.\.tools\android-sdk\platform-tools\adb.exe install -r "$env:LOCALAPPDATA\VISION\field-build\outputs\apk\debug\app-debug.apk"
$env:API_BASE_URL = "http://127.0.0.1:8080"
npm.cmd run dev:web
```

Enter the ephemeral token and `http://127.0.0.1:8765` on the phone. Open
`http://localhost:3000/lab/live` on the desktop with the same pairing information.
Wait for the desktop worker to report ready. If memory falls below its reserve,
or the worker times out, end the session and resolve the reported cause before
reconnecting. A new session ID requires a new clock exchange.

Use `/lab/session` for opt-in event recording and structured export. Recording is
off by default and exports exclude raw camera and audio data. Use `/lab/review` for
the thirty predefined source windows. Review exports preserve the original
packet hash and keep incomplete judgments pending.

Stop the phone session before stopping the gateway with Ctrl+C. To remove USB
forwarding, run `adb reverse --remove tcp:8765`. A phone callback estimates
playback start. Physical earbud latency requires separate measurement.

## Wireless Product V1.1

For pinned TLS and QR pairing without per-session USB, follow
[the wireless guide](VISION_WIRELESS_ALPHA_FIELD_GUIDE.md). Private desktop pages
now require `/lab/login`; see [web setup](VISION_PUBLIC_WEB_DEPLOYMENT.md).
