# Local V0 demo output contract

`tools/rescue_export.py --run <completed-run> --output <new-directory>` produces
`manifest.json` and streamed `frames.jsonl` for a future dashboard. It refuses
incomplete runs and refuses to overwrite an output directory.

Each version-1 frame packet includes source frame identity/PTS, mode, dimensions,
detections, track IDs/boxes, world state, corridor, trajectory, interaction, risk,
attention, alert output/text, source-to-publication age, provider state and
failure/degraded diagnostics. The manifest retains source/configuration hashes.

An absent field or null observation is unavailable, not a successful empty
measurement. Offline wall-clock source age is null, not zero. Consumers must show
the mode and degraded state and must not relabel offline text as live alerts.
Provider states may be null for legacy traces that did not capture them.

No raw video, frames or model tensors are embedded. This is a local structured
export, not a hosted website or a production safety interface. Physical-accuracy
and production-safety validation fields remain false.
