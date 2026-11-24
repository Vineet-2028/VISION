# Coverage and review protocol

Use `tools/v0_analyze.py` with the exact Task 018 reference file,
`datasets/tracking_v1/sentinel-track-review-prototype.json`. Preserve the source
hash gate, the 188 central-reference event denominator and the same-frame linked
stage prefix. Conditional coverage and end-to-end coverage are separate outputs.
Missing realtime observations are not automatically detector classification misses.

Do not merge Task 014's 52-event proxy, Task 016's 1,507 entity episodes or the
Task 018 population. They do not establish hazard recall. Rescue runs with changed
cadence/provider availability must declare those configuration differences.

`tools/rescue_tracking.py` separately evaluates 300 fixed reference frames using
nearest runtime updates within 100 ms, observed tracks only and class-aware IoU
0.5. Clip-local identity accounting prevents cross-clip ID collisions. It also
reports observed track lifetimes, prediction-only ages and tracking gap resets.
These prototype identity labels are not independently validated tracking truth.

## Human review

The exact 30 original timestamp windows are preserved in the new packet under
`benchmark-results/v0-rescue/human-review`. No relevance, interruption or usefulness
judgement has been generated automatically. Original labels, if any, are retained
as prior labels; new rescue judgements remain unanswered and unadjudicated.

From the repository root:

```powershell
apps/perception-lab/.venv/Scripts/python.exe tools/v0_review.py --packet benchmark-results/v0-rescue/human-review --serve
```

Open <http://127.0.0.1:8918>. Inspect each clip, choose a relevance label and an
interruption judgement, enter notes and download the JSON. The server binds only
to loopback, serves allowlisted files and does not upload answers. Closing the
browser without downloading does not save edits. Downloaded labels require
adjudication before use as evaluation truth.

Human usefulness remains **NOT VALIDATED** while this review is pending.
