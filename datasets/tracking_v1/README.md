# Task007 local track review

## Current prototype version

The user accepted prototype-level data quality and authorized removal of unusual
labels on October 18. `sentinel-track-review-prototype.json` is the active prototype
evaluation copy: 31 suspect TRAIN annotations removed, 12,008 annotations retained.
`prototype-cleanup.json` records the transformation and hashes. The original draft
and `sentinel-track-review.json` remain unchanged. Other classes/IDs were not altered.

This removes the annotation-refinement blocker for local prototype work only.
Reference objects may now be missing; generated IDs remain model-assisted. Scores
are prototype diagnostics, not independent identity/safety qualification. See the
[prototype closeout](../../docs/research/results/task007-prototype-accepted-2026-10-18.md).
The instructions below remain available for future refinement. Use new output names
when rerunning evaluations; existing results are preserved.

## Review workflow for future refinement

This packet contains **300 draft frames and 727 proposed clip-local IDs**, not tracking ground truth: three 20-second
windows starting at 50, 230 and 450 seconds, sampled at 5 FPS from the user-owned
recording. Source pixels, proposal JSON and generated editor remain Git-ignored.
The clips are development windows from one recording, not independent qualification data.

Open `review.html` in your local browser. Keep it beside `frames/`. Select a box to
edit its ID/class or redraw/delete it; draw missed visible P0 objects. Preserve the
same ID for the same object within a clip, including defensible short occlusions.
Correct erroneous links at crossings. Use a new ID when identity is uncertain.
Do not invent boxes for fully hidden objects. Delete a false TRAIN box on a shelter;
a shelter is context, not a P0 tracked class. Task006 shelter annotations stay unchanged.

Inspect the **whole frame**, label scene/motion/occlusion where defensible, and mark
each frame reviewed only after checking it. Save regularly using **Save review JSON**;
the editor has no automatic storage. Resume by loading that saved JSON. Save the final
download as `datasets/tracking_v1/sentinel-track-review.json`. No upload is needed.

From the repository root, in PowerShell:

```powershell
Start-Process .\datasets\tracking_v1\review.html
```

After completing review:

```powershell
$python = ".\apps\perception-lab\.venv\Scripts\python.exe"
& $python tools/prepare_tracking.py validate-review --draft datasets/tracking_v1/draft.json --review datasets/tracking_v1/sentinel-track-review.json
& $python tools/tracking_benchmark.py real --draft datasets/tracking_v1/draft.json --review datasets/tracking_v1/sentinel-track-review.json --predictions benchmark-results/task007/picodet-cache.json --publication-threshold 0.25 --output benchmark-results/task007/picodet-reviewed.json
& $python tools/tracking_benchmark.py real --draft datasets/tracking_v1/draft.json --review datasets/tracking_v1/sentinel-track-review.json --predictions benchmark-results/task007/yolox-cache.json --publication-threshold 0.15 --output benchmark-results/task007/yolox-reviewed.json
npm run verify
```

Outputs are exclusive: choose a new name for another run. The evaluator rejects draft
statuses, duplicate per-frame IDs, altered frame identities and image hashes. Passing
validation proves structural consistency; it cannot prove a human linked objects correctly.
Compare results and inspect failure cases before selecting a tracker or approving Task008.

The two cached detector runs use identical JPEG input pixels and a .10 proposal floor.
`predictions.json` beside the draft was generated on original decoded pixels for proposal
preparation; it is not the fair comparison cache. Never use generated IDs as truth.

To prepare a new packet (requires the private Task006C video, weights and calibration):

```powershell
& $python tools/prepare_tracking.py prepare --video "datasets/sentinel_first_person_v1/raw/Screen Recording 2026-10-16 223504.mp4" --config benchmark-results/task007/picodet-tracking-5hz.config.json --output datasets/tracking_v1/new-packet --starts 50 230 450 --duration 20 --fps 5
```

Preparation refuses an existing output directory. Keep any new private packet Git-ignored
before generation. The existing packet is ready; regeneration is unnecessary.
