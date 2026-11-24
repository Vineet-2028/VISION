# V0 rescue baseline

The Task 018 canonical results remain unchanged. Hashes of its reports and run
manifests are retained in `benchmark-results/v0-rescue/task018-preservation.json`.
The raw Task 018 traces remain in their original directories.

| Measurement                  | Task 018 canonical | Unchanged rescue reproduction |
| ---------------------------- | -----------------: | ----------------------------: |
| Realtime processed frames    |                 62 |                           136 |
| Dropped frames               |             17,939 |                        17,865 |
| Processing failures          |                  0 |                             0 |
| Publication interval P95     |      11,001.493 ms |                 4,405.5113 ms |
| Publication interval maximum |      12,401.919 ms |                67,004.4972 ms |
| Pipeline elapsed             |          605.079 s |                     614.743 s |
| Including setup              |          644.286 s |                     642.487 s |

The reproduction used the same model/configuration inputs and 600-second source
interval before rescue runtime edits. Its different timing is not an optimization
result. Host scheduling/power/load were not controlled; the long maximum interval
must remain visible. Source hash, model hashes, provider configuration, machine
summary and configuration hash are in `baseline/manifest.json` and
`baseline/configuration.json`. The recorded Git HEAD does not identify the full
dirty working tree; it must not be represented as a clean release commit.

The canonical offline baseline remains 18,000 processed, one boundary drop,
zero failures and 60 accepted text outputs. Its 188-event central-reference funnel
is a prototype reference population, not hazard recall.

Historical evidence remains separate: Task 014 proxy 3/52; Task 016 conditional
episodes 60/1507; Task 017 3,579 expired and zero live alerts; Task 018 1,239 expired
and zero live alerts. These have different denominators and configurations.

Reproduction command, from the repository root:

```powershell
apps/perception-lab/.venv/Scripts/python.exe tools/v0_replay.py --config benchmark-results/task018/canonical-01/realtime/configuration.json --output benchmark-results/v0-rescue/baseline-new --mode REALTIME --seconds 600
```

Use a new output directory; the tooling refuses to overwrite an existing run.
