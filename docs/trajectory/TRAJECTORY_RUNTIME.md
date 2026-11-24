# Runtime and reproduction

Run from repository root in PowerShell:

```powershell
apps/perception-lab/.venv/Scripts/python.exe tools/trajectory_benchmark.py --output benchmark-results/task013-new-synthetic.json
apps/perception-lab/.venv/Scripts/python.exe tools/trajectory_benchmark.py --config benchmark-results/task011/offline.config.json --seconds 15 --evaluate --output benchmark-results/task013-new-retrospective.json
apps/perception-lab/.venv/Scripts/python.exe tools/trajectory_benchmark.py --config benchmark-results/task011/full.config.json --seconds 600 --output benchmark-results/task013-new-long.json
npm.cmd run verify
```

Replay configs/footage are private local artifacts, not distributable fixtures. Use configs/perception-lab.trajectory.example.json as the portable starting point with actual input/calibration/model paths. Output must not already exist. Add --overlays with a new private folder for at most8 debug images. GUI overlay is opt-in. No image writes occur in the normal predictor path.

Measure predictor compute separately from WorldState arrival cadence. RSS includes upstream models/JVM. Do not run simultaneous model replays for throughput qualification. Avoid Maven clean while a replay JVM owns the Guardian JAR. On Windows use a fresh nonsynced temporary folder for pytest and forward slashes in PYTEST_ADDOPTS; backslashes can be consumed by argument parsing.
