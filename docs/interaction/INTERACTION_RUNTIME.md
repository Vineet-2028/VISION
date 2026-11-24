# Runtime and reproduction

IMPLEMENTED: add `interaction: {}` alongside `world_model`, `corridor`, `trajectory`. It is disabled by default. Recording schema9 adds InteractionAnalysis without removing older fields. GUI/debug overlays are optional and use neutral labels; at most8 benchmark PNGs are written into a new private folder.

Run from repository root in PowerShell:

```powershell
apps/perception-lab/.venv/Scripts/python.exe tools/interaction_benchmark.py --output benchmark-results/task014-new-stress.json
apps/perception-lab/.venv/Scripts/python.exe tools/interaction_benchmark.py --config benchmark-results/task011/offline.config.json --seconds 15 --evaluate --output benchmark-results/task014-new-evaluation.json
apps/perception-lab/.venv/Scripts/python.exe tools/interaction_benchmark.py --config benchmark-results/task011/full.config.json --seconds 600 --output benchmark-results/task014-new-long.json
$taskTemp = (Join-Path $env:TEMP ('sentinel-verify-' + [Guid]::NewGuid().ToString('N'))).Replace('\', '/')
$env:PYTEST_ADDOPTS = '--basetemp=' + $taskTemp
npm.cmd run verify
git diff --check
```

Private replay configs/footage are local artifacts. Portable configs/perception-lab.interaction.example.json is a wiring template, not a model-filled demo; provide actual detector/tracker/model/input paths. Output files must not already exist. Optional `--overlays benchmark-results/task014-new-images` requires a fresh directory.

Avoid concurrent model replays/builds during performance measurements. Never run Guardian clean while a replay JVM owns its JAR. Windows pytest should use a fresh nonsynced temp directory with forward slashes in PYTEST_ADDOPTS. Full-pipeline latency includes upstream inference; predictor and interaction compute are reported separately. High entity-count stress is not a wearable deadline guarantee.
