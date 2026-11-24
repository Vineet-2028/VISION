# Diagnostic candidate capture

Status: capture implementation and recorded-source regressions are available,
but readiness is on security hold. See the current
[verification report](../research/results/VISION_ALPHA_V1_1_FINAL.md).
No Alpha V1.1 promotion or physical phone validation is claimed.

The opt-in desktop observer is selected with:

```powershell
.\apps\perception-lab\.venv\Scripts\python.exe tools\wireless_alpha.py --address 192.168.1.52 --diagnostic-candidate
```

Use the current PC Wi-Fi address if it has changed. Start this only for a
supervised session. Inference runs for the session lifetime; Stop ends capture
and Ctrl+C closes the gateway. The real model has now passed a synthetic-input
CPU smoke; that is not a physical phone validation or an accuracy result.

Enable Save new events in Android History. Report a problem opens the marker
controls. Camera buffering requires its own checkbox. The rolling buffer stores
at most 24 frames, 4 MiB of JPEG data and two seconds before the marker. It has
no post-marker interval yet. Only frames actually submitted to transport are
buffered. This does not cover every CameraX capture or discarded pending frame.

Marking feedback with buffering enabled saves one encrypted clip. An existing
retained clip is protected from replacement. Export it and explicitly delete
the retained copy before saving another case.
Stopping clears RAM and revokes buffering consent. The saved clip has a 24-hour
expiry checked at startup, export and periodic cleanup; scheduled cleanup may
be delayed by Android. Delete saved diagnostic clip removes it immediately.
Deleting all History also clears the buffer and saved clip.

Export readable diagnostic clip creates a plaintext binary export at the
user-selected destination through Android's document picker. Share it only
deliberately. No plaintext cache file is created by the app. The local encrypted
copy uses Android Keystore. The export includes the session and source sequence,
camera monotonic timestamps, rotation, dimensions and JPEG frames.

The phone now offers a recent submitted-capture selector. A selected capture is
recorded as USER_SELECTED_FRAME; the default is LATEST_SUBMITTED_FRAME. Neither
is independently annotated object identity. If the selected frame has left the
rolling buffer, feedback is saved without inventing a clip.

## Capture and inspect one case

1. Start the candidate launcher, pair the phone, enable History, and start a
   supervised phone session.
2. On the PC pairing page, click Start diagnostic event recording. This saves
   structured events in bounded session memory. Keep the gateway running.
   Start only when ready for a short case. Total event storage is capped at
   8 MiB; detailed entity evidence has a separate budget. Refresh the PC page to
   inspect recording status. If FULL, export immediately and begin a new session
   for the next case; later frames do not restore omitted evidence.
3. In the phone's Report a problem dialog, enable camera buffering, then close
   the dialog. Reproduce the scene, reopen the dialog and select the capture.
   Mark the feedback. The clip contains only the available preceding frames.
4. Stop the phone session. Export readable diagnostic clip and export History
   on the phone. Transfer the chosen files to your PC yourself.
5. On the PC pairing page, export saved gateway events before closing the
   gateway or starting a new session.
6. Import the three matching exports. The commands below assume you placed them
   in Downloads with the suggested export names.

```powershell
$caseRoot = Join-Path $env:LOCALAPPDATA "VISION\diagnostics\case-01"
.\apps\perception-lab\.venv\Scripts\python.exe tools\import_field_case.py --clip "$env:USERPROFILE\Downloads\vision-diagnostic-frames.bin" --gateway "$env:USERPROFILE\Downloads\vision-gateway.zip" --feedback "$env:USERPROFILE\Downloads\vision-history.json" --output $caseRoot
.\apps\perception-lab\.venv\Scripts\python.exe tools\replay_field_case.py --case $caseRoot --output (Join-Path $caseRoot "input-replay.json")
$env:VISION_DIAGNOSTIC_CASE = $caseRoot
$env:VISION_LAB_MEDIA_ENABLED = "1"
$env:VISION_LAB_SECRET = node -e "process.stdout.write(require('node:crypto').randomBytes(32).toString('hex'))"
Write-Output $env:VISION_LAB_SECRET
npm run dev:web
```

Open `/lab/login` at the local address printed by Next.js. Enter the locally
printed Lab secret, then open `/lab/diagnostics`. The viewer supports frame
stepping, seek, timed playback, exact-frame accepted/rejected candidate overlays,
entity evidence selection and recorded packet inspection. A missing or earlier
detector source never gets boxes drawn on the current frame.

The import directory contains authorized plaintext media and private evidence.
Use a non-synced folder such as the LocalAppData location above. This repository
is under OneDrive: Git ignore rules do not control filesystem synchronization.
Never add real clips to public assets or source control. Imported copies require
separate manual deletion. Choose a new case directory for each import.

`input-replay.json` verifies and replays the saved bytes, sequence, camera time,
rotation and recorded output. Neural recomputation is explicitly NOT_RUN.
The rolling clip lacks the full preceding tracker, semantics and attention state;
exact full-engine equivalence cannot be claimed from this artifact alone.

For an additional cold-start detector comparison, with at least 3 GiB RAM free:

```powershell
.\apps\perception-lab\.venv\Scripts\python.exe tools\replay_field_case.py --case $caseRoot --output (Join-Path $caseRoot "detector-replay.json") --recompute-detector
```

This uses one CPU thread per detector, the pinned model and frozen release
configuration. It stops below a 2 GiB RAM reserve. It verifies baseline/candidate
detection parity and records paired timings, including warmup; this is not a
realtime performance qualification. Camera timestamps are retained and the
detector clock is rebased to clip start. Tracking, policy, speech and original
scheduling are not reproduced. Missing or different recorded release hashes
are rejected. Output files are never overwritten. The model runs once in an
isolated child, with baseline inference and observer inference sharing that one
session. The authenticated Lab reads `detector-replay.json` only when its session,
frame, timestamp and JPEG hash match the recorded packet. Original decisions
remain separate. The current real-model smoke used synthetic input only.

## Six supervised cases

Use a stationary setup or a controlled sighted-developer session. Do not rely on
VISION for navigation, cross traffic for a test, or deliberately create a hazard.
Avoid identifiable bystanders and obtain permission for any retained footage.
Keep the phone and PC on the same trusted network. Confirm the app connects
before enabling recording. Hardware behavior remains to be verified by the tester.

| Case                      | What to observe and record                                                                                                          |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Correct name              | Show a known object, note its actual identity and the exact words heard.                                                            |
| Generic Object            | If naturally produced, mark Wrong name and record the actual object; do not label a generic utterance as proof of detector failure. |
| Visible but undetected    | Mark Missed promptly; independently annotate the exported image rather than using model boxes as truth.                             |
| Relevant but silent       | Record why the object matters and its position; silence may be appropriate under current risk/attention rules.                      |
| Irrelevant and silent     | Mark Correct silence and describe the object and why no alert was needed.                                                           |
| Stale/unnecessary warning | If naturally observed, mark Unnecessary warning and record timing/context and what was actually heard.                              |

For **each** case:

1. Enable both History and the separate capture-buffer consent. Start structured
   event recording on the PC. Verify the current session before proceeding.
2. Present the object safely, then promptly select the intended recent capture
   and mark the case while it remains in the two-second buffer. A marker without
   a saved clip is not usable image evidence; capture a new consented case.
3. Stop phone capture. Export readable diagnostic clip, History, and the matching
   gateway ZIP immediately. Do not close the gateway or start another session
   before its export. Name the files with the same local case identifier.
4. Import into a new directory using the commands above. If session/frame/time
   validation fails, keep the originals and do not force a match.
5. Inspect the clip and independently annotate visible objects, including missed
   ones. Record exact speech and whether it came from the phone or Bluetooth.
   TTS callbacks alone do not prove the user heard it. Do not mark unread pages reviewed.
6. Verify the exports are usable before explicitly deleting the retained phone
   clip; otherwise the app will protect it from replacement. Delete authorized
   plaintext copies separately when no longer needed.

If a case does not occur naturally, record NOT_OBSERVED rather than manufacturing
the expected behavior. Maintain six case outcomes, including failed captures and
UNKNOWN evidence. None of these tests authorizes promotion by itself.

PicoDet diagnostic counts begin after embedded vendor NMS. Pre-NMS rejection
counts are unavailable with the installed model. Missing reasons remain UNKNOWN.

## Release-closure capture indicators

Report a problem now shows buffer ENABLED/DISABLED, whether an encrypted clip is
retained, and the selected/latest submitted capture's session ID. Confirm the same
session on the PC. The phone does not mirror PC recording status: the PC operator
page is the authority for RECORDING / FULL. On FULL, export immediately and start
a new session; do not assume later frames were retained.

A successful marker explicitly distinguishes saved feedback from saved encrypted
images. Export both the diagnostic clip and History, then the matching PC gateway
ZIP. Export confirmation means the selected document stream completed, not that a
remote storage provider has synchronized it. Exported files are readable; prefer
a non-synced local folder and delete them separately after review. The app protects
a retained clip from replacement until explicit deletion. Retention scheduling can
be delayed by Android; startup/export also apply the 24-hour expiry check.

The new importer preserves later detector publications separately from capture
identity and adds bounded causal references. UNKNOWN remains UNKNOWN without an
independent reference annotation. Screenshots from browser QA use synthetic
images and cannot qualify a physical field case.
