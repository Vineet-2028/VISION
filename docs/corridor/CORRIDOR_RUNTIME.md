# Runtime and development

IMPLEMENTED: enable `world_model: {}` and `corridor: {}` in a LabConfig. The example is `configs/perception-lab.corridor.example.json`; supply a permitted local video and its matching calibration metadata before running. UNKNOWN calibration supports image fallback. The synthetic 8x6 example calibration is a test fixture, not valid physical calibration for real footage.

From repository root in PowerShell:

```powershell
npm run check:core
npm run check:lab
apps/perception-lab/.venv/Scripts/python.exe -m perception_lab.cli --help
apps/perception-lab/.venv/Scripts/python.exe tools/corridor_benchmark.py --output benchmark-results/corridor-stress-new.json
apps/perception-lab/.venv/Scripts/python.exe tools/corridor_benchmark.py --config "configs/your-local-corridor.json" --seconds 600 --output benchmark-results/corridor-replay-new.json
npm run verify
git diff --check
```

Use new output paths; measurement tools refuse to overwrite evidence. Optional `--overlays <new-private-directory>` exports at most eight annotated PNGs; footage stays local and ignored by Git. GUI visualization adds neutral corridor/relation/sample labels when enabled. Rendering/JSON/debug writes occur outside the analyzer's compute timer and can slow diagnostic runs; production benchmarking disables overlays and session recording.

Recording schema7 adds compact CorridorAnalysis to optional FrameResult recording. Prior schema1–6 records remain readable; world-only records remain schema6. Metrics include corridor duration and published-analysis count. A replacement analyzer only needs `analyze(WorldState)`; it owns no mandatory lifecycle resource or worker.

Complexity is O(N + S), N<=512 entities and S<=768 samples, each against a bounded polygon. No pairwise entity comparisons, world-history scans, global mutable state or snapshot backlog. Configuration/provenance hashes are cached at construction. The existing JVM is initialized once. Run Maven checks before Python replay processes, because Windows may hold the JAR open while a JVM is active. Windows `core-check` now clears OneDrive-restored read-only attributes on directories within the fixed generated Guardian target before Maven clean. It rejects links and never changes source files; it cannot release a JAR held by a live process.
