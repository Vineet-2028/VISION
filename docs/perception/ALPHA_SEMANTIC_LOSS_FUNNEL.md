# Alpha semantic loss investigation — October 29

Historical checkpoint: implementation statements below describe October 29, not
the current adapter/fusion implementation. See
[the release completion work record](ALPHA_RELEASE_COMPLETION_PROGRESS.md) for
current engineering and qualification status. The frozen forensic evidence remains
valid; it does not establish current-run semantic accuracy.

Status: forensic baseline ledger completed; runtime recovery is not yet measured.
Task019 has not started. No acceptance threshold or expiry was relaxed.

## What the original evidence establishes

The frozen 60 delivered alerts all retain non-UNKNOWN categories in their linked
track and world records: 30 CAR, 14 PERSON, 10 TRUCK, 4 MOTORCYCLE, 2 BUS.
All 60 alert intents explicitly contain `SEMANTICS_UNAVAILABLE`; all presentations
say `Object.`. Category presence is not evidence of temporal semantic authorization.

Exact original detector-box association succeeds for 38 events. For 22, the
ledger records UNKNOWN association. It does not substitute a new detector run,
nearest box or IoU overlap for the original track association. The earlier 60/60
named-overlap proxy remains a different measurement.

The frozen replay serializer deliberately excluded `semantic_evidence`. Its world
projection also omitted semantic fusion state. Consequently the historical trace
cannot establish the first authorization-loss stage, semantic stability, provider
calibration, or whether a particular rejection was due to expiry or confidence.
The ledger reports these missing fields explicitly rather than inventing reasons.
First confirmed unavailable stage: ALERT_INTENT_SEMANTIC, 60/60.
First semantic loss stage from recorded telemetry: UNKNOWN, 60/60.

Inspection of the archived `attention.py` and `pipeline.py` also found no
semantic-evidence producer in the rescued attention path. This is an architecture
finding, not proof that the historical detector labels met today's fusion gates.
The current implementation has a world-to-attention attachment path, but the real
PicoDet adapter still emits legacy detections; it does not supply generic semantic
observations. The general joint-score adapter conservatively marks observation
quality UNKNOWN, while fusion requires GOOD evidence for stable support. Neither
condition should be bypassed solely to increase specific wording.

## Changes for the next measurement

- New replay traces use schema 2, retain attention semantic evidence and its
  provenance, and retain bounded world entity observation/fusion state.
- Attention attachment records explicit authorization/rejection reasons: missing
  association/evidence, replaced track, unstable semantics, expired/future/missing
  timing, missing authorized concept, or authorized stable specific concept.
- These diagnostics do not change risk decisions, confidence gates, expiry or
  presentation wording.
- `tools/semantic_event_ledger.py` checks the frozen trace hash, exact alert IDs,
  entity identity, publication frame, source timestamps and all 60 outputs.
  Missing/duplicate events fail; output files are exclusive-created.

## Reproduce the forensic ledger

From the repository root in PowerShell, choose a new output filename:

```powershell
& apps/perception-lab/.venv/Scripts/python.exe tools/semantic_event_ledger.py --output benchmark-results/v02/semantic-event-ledger-baseline-new.json
```

Executed artifact: `benchmark-results/v02/semantic-event-ledger-baseline-01.json`.
It contains eight stage records per event, original recorded evidence, explicit
unknowns, population/trace hashes and before counts. After counts remain null.

## Required next evidence

Connect a qualified real semantic observation path, retain existing stability and
freshness gates, and rerun the exact population with complete instrumentation.
Only then report before/after specific, broad-group and generic counts. Independent
broad-group stability, GPU process isolation, rotated downstream runs, heading
integration and final offline/realtime regressions remain open. No Alpha release
is frozen and no semantic recovery improvement is claimed at this checkpoint.
