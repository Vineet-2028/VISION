# Local runtime and reproduction

Enable `risk: {}` with `world_model: {}`. For full forecasting also enable corridor, trajectory and interaction. `configs/perception-lab.risk.example.json` is a wiring template: supply actual local input/model paths. Risk defaults off and adds no inference or dependencies.

From the repository root in PowerShell:

```powershell
apps/perception-lab/.venv/Scripts/python.exe tools/risk_benchmark.py --output benchmark-results/risk-new-stress.json
apps/perception-lab/.venv/Scripts/python.exe tools/risk_benchmark.py --config benchmark-results/task011/offline.config.json --seconds 15 --evaluate --output benchmark-results/risk-new-proxy.json
apps/perception-lab/.venv/Scripts/python.exe tools/risk_benchmark.py --config benchmark-results/task011/full.config.json --seconds 600 --output benchmark-results/risk-new-long.json
apps/perception-lab/.venv/Scripts/python.exe tools/risk_review.py --packet benchmark-results/task015/review-packet --serve
```

Review opens at http://127.0.0.1:8915. The server exposes only its manifest, page and one configured local video; no directory browsing, write endpoint or upload. Stop with Ctrl+C. Review JSON downloads locally. Footage, paths, images and review files remain ignored. Portable recreation: `tools/risk_review.py --config <local-config> --packet <new-private-folder>`.

Use fresh output paths; existing measurements are never overwritten. Run performance measurements sequentially, without simultaneous model replays or Guardian clean/build. Temporary system-awake requests may be used for the ten-minute Windows measurement and must be released afterwards.

```powershell
$taskTemp = (Join-Path $env:TEMP ('sentinel-verify-' + [Guid]::NewGuid().ToString('N'))).Replace('\', '/')
$env:PYTEST_ADDOPTS = '--basetemp=' + $taskTemp
npm.cmd run verify
git diff --check
```

Task016 attention and Task017 presentation are not implemented. The risk overlay is an engineering view only.
