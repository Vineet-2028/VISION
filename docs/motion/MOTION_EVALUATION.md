# Motion evaluation

IMPLEMENTED analytical tests: ordered time/session/calibration contracts; vector resize; known pure rotation and zero motion; essential translation direction; nonidentity IMU mount; exact frame-A depth/PnP; independent-object residual; observed/predicted track distinction; immutable bounded arrays; provider replacement and deterministic visual estimates.

MEASURED evidence is linked from the Task009 report. motion_benchmark.py compares LK and DIS on hashed local prototype frames, with and without exclusion boxes. Excluded boxes denote potentially dynamic classes, not verified moving objects. Unmasked regions are not verified static truth. Do not report ROC/AUC, pose accuracy or background-separability ground truth from these annotations.

Long replay uses tools/measure_replay.py, a bounded recent latency window and sampled process-tree RSS. Start RSS includes startup and is not a warmed leak baseline. Counts include explicit unavailable states, drops and failures. Shared desktop load may affect timings. The existing source is a screen recording with placeholder calibration; PTS is authoritative recording time, not verified camera exposure time.

UNVALIDATED/NOT EXECUTED: synchronized real IMU agreement, independently labeled crowd/night/high-head-motion subsets, trajectory ground truth, optional public flow/trajectory benchmarks and learned flow. No dataset download is required for prototype completion. Flow-assisted tracking is deferred; Task007 remains independent and unchanged.

Commands (PowerShell, repository root):

```powershell
apps/perception-lab/.venv/Scripts/python.exe -m pytest apps/perception-lab/tests/test_motion.py
apps/perception-lab/.venv/Scripts/python.exe tools/motion_benchmark.py --packet datasets/tracking_v1/sentinel-track-review-prototype.json --calibration benchmark-results/task006c/replay-calibration.json --output benchmark-results/task009/new-comparison.json --limit 20
npm run verify
```

Run full verification after replay processes exit: Windows locks the Guardian JAR while the JVM uses it, so Maven clean must not run concurrently with replay.

Calibration gate: UNKNOWN/INVALID calibration cannot produce visual ego-motion, research PnP or projected compensation. The available real recording uses an identity-only UNKNOWN calibration, so real camera-motion/residual metrics are unavailable. Analytical tests use explicit synthetic valid geometry. Supply measured calibration before interpreting real camera-motion evidence.

`tools/motion_replay.py` is a bounded offline diagnostic: it decodes source PTS but samples before RGB conversion, retaining only the recent pair. It records source coverage, deliberate sampling omissions, pair counts, explicit failures, bounded latency windows and RSS. Its processing-age metric is not real-time freshness. The standard CLI real-time run failed to keep up and remains separately reported.
