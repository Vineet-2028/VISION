# V0 offline technical evidence pack

Status: READY_OFFLINE. This is an engineering prototype demo, not realtime or safety validation.

| Mode     | Processed | Dropped | Failures | Text accepted | Pipeline seconds | Including setup seconds |
| -------- | --------- | ------- | -------- | ------------- | ---------------- | ----------------------- |
| Offline  | 18000     | 1       | 0        | 60            | 3106.501         | 3144.303                |
| Realtime | 62        | 17939   | 0        | 0             | 605.079          | 644.286                 |

Show the local source with examples-final diagnostics and text; label it OFFLINE REPLAY. Show a silence example and the zero-live-alert result, not only successful text examples. Then show the proxy denominator and reference limitations. The full report records candidate expiry ages, compute, memory and top-five rescue experiments.

```powershell
apps/perception-lab/.venv/Scripts/python.exe tools/v0_review.py --packet benchmark-results/task018/canonical-01/examples-final --serve
```

Open http://127.0.0.1:8918. The server is read-only and local; it is not running automatically. Downloaded labels are not automatically validated.

Do not claim human hazard recall, blind-user benefit, metric motion accuracy or production safety. No inference that a test count proves usefulness. See [snapshot](V0_BENCHMARK_SNAPSHOT.md), [full report](task018-v0-2026-10-25.md), and [machine-readable pack](V0_YC_EVIDENCE_PACK.json).
