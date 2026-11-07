# Local Alpha demo

The demo plays the existing local recording and retrieves measured Guardian
updates by source timestamp. Seeking, stepping and playback speed change the
viewer position. They do not run inference or generate new alerts.

Prepare the byte index once if the local replay has no `demo-index.json`:

```powershell
.\apps\perception-lab\.venv\Scripts\python.exe tools/alpha_demo_index.py benchmark-results/v02/alpha-full-realtime-01 benchmark-results/v02/alpha-full-realtime-01/demo-index.json
```

From the repository root, configure the API origin (the replay itself works
with the API stopped) and start the website:

```powershell
$env:API_BASE_URL = "http://127.0.0.1:8080"
npm.cmd run dev:web
```

For the already-built production bundle, use
`npm.cmd run start --workspace @sentinel/web -- --hostname 127.0.0.1 --port 3000`.
The health page reports API unavailable when that service is stopped. Open
[the replay](http://localhost:3000/lab/replay), [the measurements](http://localhost:3000/lab/metrics),
or [the review windows](http://localhost:3000/lab/review). The replay checks the
local video hash before serving it. The index points into the measured trace,
so the demo does not need another copy of the video or trace.

The human reviewer chooses both a relevance judgment and an interruption
judgment for a window to count as reviewed. Notes are optional. Export before
closing the page. Review output is a separate file linked by SHA-256 to the
original machine packet.

## Product V1.1 access change

The public `/demo` no longer serves research footage. Configure the operator secret
and sign in at `/lab/login` as described in
[the web guide](../releases/VISION_PUBLIC_WEB_DEPLOYMENT.md). Raw video remains off
unless `VISION_LAB_MEDIA_ENABLED=1` is explicitly set after media-rights review.
