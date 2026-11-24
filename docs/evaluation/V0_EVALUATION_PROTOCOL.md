# V0 evaluation protocol (Task018)

Task018 freezes the intelligence loop through Task017. It adds measurements, reference accounting and review artifacts. It does not tune expiry, change models, implement audio, or begin Task019. The next implementation phase is V0_RESCUE_PASS.

## Reproduce locally

Use the repository's installed Python environment, Java toolchain and approved local model/video files. Run `npm.cmd run verify` first. Do not rebuild Guardian while a replay JVM is using its JAR.

```powershell
npm.cmd run evaluate:v0 -- --config benchmark-results/task011/full.config.json --output benchmark-results/task018/new-run
```

The historical local config path is an example, not a portable bundled dataset. On another machine supply a `LabConfig` with the same approved source, calibration and model hashes. Relative paths resolve against that config. The runner enables default corridor, trajectory, interaction, risk, attention and alert stages when absent; explicit nondefault stage configuration is preserved. The frozen effective configuration is written into each run. Canonical realtime requires a REALTIME input configuration with an explicit drop policy and freshness bound. Offline changes mode to OFFLINE_REPLAY, drop policy to PROCESS_ALL and removes the realtime staleness bound. No source subsampling is performed.

The command creates a new output directory, freezes source/dependency hashes, prepares a blind packet, runs 600 source seconds in realtime and offline sequentially, analyzes both, performs a bounded eight-profile ablation and benchmarks reasoning on 16 real frozen snapshots. Failures return nonzero. Existing run directories are not overwritten. Raw output can occupy several gigabytes; it remains private under ignored `benchmark-results/`.

For analysis revisions use `v0_analyze.py --output <new-directory>` rather than overwriting prior evidence. A partial replay is rejected. Reference and review source hashes must match. Reviewed labels are rejected by the draft importer pending separate adjudication, rather than silently downgraded or promoted.

## Reference populations and denominators

1. Historical 30 six-second Task015–017 windows: retained as drafts, with frozen historical counts and current-run window counts kept separate.
2. Blind 30 six-second windows: seed 18001, one uniform timestamp within each equal 20-second source stratum. Selection reads source identity and duration only, never predictions. Scenario diversity is unknown until review; one recording does not establish deployment diversity.
3. Task007 prototype identity annotations: explicitly PROXY, never independent human interaction truth. One source event is a clip/reference-track ID. Proxy relevance means an annotated bottom center occurs in normalized x=[0.4,0.6], y>=0.65. This is an image occupancy heuristic, not a hazard definition. Relevant events are evaluated only at their central-occupancy reference observations. Draft-origin ID fragmentation limits event independence.

The proxy matching rule is exact category plus IoU>=0.5 against the nearest annotated frame within 100 ms. Tracks must be observed. Downstream records must link the same runtime track/entity in that update. A stage passes only when all preceding stages in that same-frame path pass. Across an event, the longest coherent path determines survival; unrelated object successes cannot fill gaps. First stage timestamps retain the earliest qualifying path observation. A source event with no aligned runtime update remains a coverage failure with explicit temporal-missingness reason, not a claim of detector classification failure.

The canonical funnel is detection, track, world entity, known corridor relation, available trajectory, non-REMAIN_OUTSIDE interaction, elevated-or-higher risk, selected non-silent attention, alert intent, READY presentation and text-sink acceptance. This is a deliberately strict operational pipeline proxy. It does not make every central object deserving of an alert. Report stage availability and source event coverage separately from physical or human correctness.

The denominator at stage N contains only relevant references with the complete preceding prefix. Missing observations are not silently excluded from source coverage. Each event is charged once at its first failed stage; raw downstream outcomes remain diagnostic evidence. HUMAN_REVIEWED, PROXY, DRAFT, AMBIGUOUS and INSUFFICIENT_EVIDENCE strata never merge. Empty denominators are null. Unreviewed windows cannot establish hazard recall, false alerts, lead time or usefulness.

## Clocks and timing

Media observation nanoseconds and `perf_counter_ns` are different clocks. Realtime due time maps the source PTS onto the replay monotonic anchor. Stage publication age is stage completion minus that mapped due time. Candidate age additionally includes the gap to its oldest reported source observation. Offline admission time is not a realtime anchor: offline wall source ages remain null. Offline alerts obey source-time expiry and cannot demonstrate live delivery.

`ComponentExecution` retains actual provider start/end. Pipeline metric callbacks retain duration and callback publication time for each stage; inferred start=end-duration has callback overhead and is not an independently instrumented CPU start. Nested component/postprocess/age distributions must never be summed. The critical-path artifact separates synchronous provider total and postprocess total. Async work requires interval-overlap analysis rather than summing its work onto the blocking path. The canonical configuration's actual async setting is recorded, not assumed.

First-500ms-crossing counts are update-level timing diagnostics. Provider ordinals reflect execution order, not permanent provider identity; raw canonical traces currently omit repeated component provenance. Exact provider names must come from configuration/execution order and ablation, not a guessed label. Publication age is not substituted for an unknown entity-specific stage age in the event ledger.

Runtime metric distributions retain 2048 recent values, with explicit scope. Offline analysis computes exact whole-run nearest-rank P50/P90/P95/P99 from streamed scalar samples. JSONL is streamed; no dense image/depth/flow arrays or world histories are retained. RSS is sampled after each update, with at most 121 timeline samples. Peak sampled RSS is not an OS-certified peak; end RSS alone is not a leak proof. Instrumentation time and large artifact I/O are disclosed, so these runs are measured research runs rather than uninstrumented production benchmarks.

## Human review

```powershell
apps/perception-lab/.venv/Scripts/python.exe tools/v0_review.py --packet benchmark-results/task018/canonical-01/blind-review --serve
```

Open <http://127.0.0.1:8918>. Inspect each clip without model overlays. Select relevant, irrelevant, ambiguous or insufficient evidence; note interaction type and missing visual context. Download the review JSON. No server write, automatic validation or upload occurs. Labels still require adjudication and event/actor linkage before hazard recall can be scored. Never mark automated review as human validation.

## Bounded experiments and limits

A decode/preprocess; B detector; C tracker; D depth; E flow/ego; F segmentation; G world; H reasoning/alerts. These cumulative three-second profiles use the same source/model configuration. One fixed-order pass has startup/cache/load confounding; differences are bottleneck clues, not proven optimization gains. Pure reasoning repeats 16 actual snapshots 20 times with fresh policy state per pass. Its throughput excludes decoding/inference and is not device-level capacity.

Success/failure examples are capped at ten per type, spaced at least six source seconds, and selected by a declared engineering criterion. No accepted alert is not necessarily a missed hazard. Zero realtime successes must remain zero; do not manufacture five successful realtime examples to satisfy a presentation quota.

Physical accuracy, human usefulness, production safety, mobile deployment, cloud scale and safety certification remain outside this engineering evaluation. The final report may declare engineering completion while retaining these as unvalidated, but must not conceal missing engineering measurements or failed verification.
