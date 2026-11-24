# Runtime and verification

IMPLEMENTED local single-writer world model, optional `world_model: {}` in lab config. `configs/perception-lab.world.example.json` is a template; replace the input/calibration with matching local identities and dimensions. Existing CLI runs it with all configured providers. No new dependency/framework or cloud runtime.

From repository root in PowerShell:

```powershell
& .\apps\perception-lab\.venv\Scripts\python.exe -m perception_lab.cli replay --config .\configs\perception-lab.world.example.json --headless
& .\apps\perception-lab\.venv\Scripts\python.exe -m pytest apps/perception-lab/tests/test_world_model.py
& .\apps\perception-lab\.venv\Scripts\python.exe tools/world_benchmark.py --output benchmark-results/task011/stress-new.json
& .\apps\perception-lab\.venv\Scripts\python.exe tools/world_benchmark.py --config benchmark-results/task011/full.config.json --seconds 600 --output benchmark-results/task011/replay-new.json
npm run verify
```

Run Maven/full verification only after replay JVMs exit: Windows locks the core JAR. Benchmark outputs are exclusive and ignored; the local full config contains private source/checkpoint paths and is not a portable checked-in configuration. The benchmark supports existing PicoDet/YOLOX, local depth and semantic adapters, and delegates execution to Pipeline. Actual measured results are in the Task011 report.

Stage distributions use bounded 2,048-sample windows. Entity/depth/surface/snapshot timings exclude benchmark bookkeeping; total consume includes counters/RSS sampling. Memory samples are bounded to 121; RSS includes model/native allocators and is not solely world-state memory. Synthetic stress uses 2,000 updates for each of 1/10/50/100/129 inputs with a 128-entity ceiling. Do not interpret shared-machine timings as isolated hardware qualification.

No raw-frame or dense map history, global singleton, thread-per-entity/source, JSON serialization in normal world updates, repeated JVM startup, or work proportional to total session length. Multiple future users map to independent per-device/session instances, not shared mutable state. Native model inference can still delay the pipeline; world state does not fix the earlier real-time throughput limits.
