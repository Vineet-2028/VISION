# Runtime and verification

IMPLEMENTED: LabConfig.attention requires explicit risk config. Pipeline invokes the replaceable engine after risk, measures attention time, records schema11, adds an optional engineering overlay and resets state on cleanup. Disabled attention preserves older recording versions. Audio defaults idle; no playback or worker starts.

```powershell
npm.cmd run verify
apps/perception-lab/.venv/Scripts/python.exe tools/attention_benchmark.py --stress --output benchmark-results/task016/stress.json
apps/perception-lab/.venv/Scripts/python.exe tools/attention_benchmark.py --config benchmark-results/task011/full.config.json --seconds 600 --primary-only --output benchmark-results/task016/long.json
apps/perception-lab/.venv/Scripts/python.exe tools/attention_benchmark.py --config benchmark-results/task011/offline.config.json --seconds 600 --packet benchmark-results/task015/review-packet/manifest.json --timeline benchmark-results/task016/windows.jsonl --output benchmark-results/task016/windows.json
apps/perception-lab/.venv/Scripts/python.exe tools/attention_review.py --source benchmark-results/task015/review-packet --timeline benchmark-results/task016/windows.jsonl --packet benchmark-results/task016/review-packet
apps/perception-lab/.venv/Scripts/python.exe tools/attention_review.py --packet benchmark-results/task016/review-packet --serve
```

Existing benchmark configs/media/models are private ignored local prerequisites. Use a fresh timeline/packet path to avoid overwriting evidence. Review server binds 127.0.0.1:8916, read-only allowlisted GET routes, no uploads or telemetry. Ctrl+C stops it. No server starts automatically.

PLANNED personalization can replace the engine or add versioned config for sensitivity, frequency, mobility aid, hearing preference and familiar environments while preserving the decision contract. Future USEFUL_ALERT/UNHELPFUL_ALERT/TOO_LATE/TOO_FREQUENT/MISSED_EVENT feedback must be explicit consented research data, not automatic learning.

Realtime integration maps processing lateness through the replay anchor into now_ns before deciding. Evidence that expired during inference cannot create an interruption intent. Offline replay deliberately uses source time to reconstruct policy behavior. This can yield entirely silent realtime output on a slow CPU; it is not proof of a useful realtime product.

The attention example config is a minimal stage-wiring example with a placeholder local video and synthetic calibration/semantics. It does not configure a detector/tracker and will not invent entities. For actual footage, add `attention: {}` to an existing permitted detector/tracker/world/risk configuration such as the local benchmark config above. Synthetic calibration supplies no physical validation.
