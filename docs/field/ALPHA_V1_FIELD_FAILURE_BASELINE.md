# Field failure baseline — 16 November 2026

Mission: VISION_FIELD_FAILURE_ROOT_CAUSE_AND_ALPHA_V1_1.
Candidate designation: ALPHA_V1_1_DIAGNOSTICS, unqualified.

## Verified provenance

Checkout HEAD is `6ec1e998d018509ef4aad915809bf625aafd4e6c` with
pre-existing tracked changes and untracked work. HEAD alone cannot reproduce it.
Frozen manifest SHA-256 is
`ecd83215cc8f8e144ec9126b61415e8ca38b854a4126cfdbc6e52d55affa6254`.
The archived runtime hash matches the manifest. All 115 archived source entries
match their recorded hashes. Detector and segmentation model files also match.
Five current paths differ from archived sources: field_export.py,
field_gateway.py, field_protocol.py, field_state.py, and tools/v0_replay.py.
These are within the field/tool exclusions explicitly implemented by the freeze
script. This does not mean the current field transport has frozen qualification.

## Current findings

- Track semantics currently normalizes JOINT_DETECTION_SCORE and
  DETECTOR_JOINT_SCORE. Historical naming mismatch is not a newly proven defect.
- Default semantic support is three frames, confidence 0.5, agreement 0.7,
  expiry two seconds. No threshold change is justified by the current evidence.
- alpha_field_worker.project filters undelivered outputs, missing lineage,
  session/lineage mismatches, missing source captures and expired presentations.
  Rejected transmission candidates have no explicit diagnostic reason in its
  current output. This is an observability gap, not proof of a field miss.
- Opt-in FieldSession recording stores publication entity IDs and outgoing
  alerts, but omits the stage decisions needed to determine the earliest loss.
- Session export contains structured events and no image/audio payloads.

## Evidence limits

ADB was executed with host access and returned an empty device list.
No phone is available through ADB for physical capture/audio verification.
The user explicitly confirmed that no failing phone session was saved and
everything was closed after testing. They observed recognition of some objects
and generic "Object" speech. Original captured images and timing are unavailable.
The new reported misses therefore have FIRST_PROVEN_LOSS_REASON UNKNOWN.
No field recall, semantic precision, acoustic latency or utility denominator
exists yet. Historical 37 specific, 2 group and 133 generic deliveries out of
172 recorded-source presentations measure wording distribution, not accuracy.

## Reproduction entry points

Run from the repository root in PowerShell:

```powershell
git rev-parse HEAD
git status --short
Get-FileHash benchmark-results/v02/VISION_CONTROLLED_ALPHA_V1/manifest.json
.\.tools\android-sdk\platform-tools\adb.exe devices
npm run check:lab
```

Use the wireless field guide for explicitly consented phone sessions. A future
diagnostic report must retain unknown stages and independent review status.
Recorded replay cannot establish physical phone-to-ear latency.
