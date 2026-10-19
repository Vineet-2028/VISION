# Performance budget

No achieved latency or validated device budget exists yet. All cells below are
unmeasured. The future camera loop may target about 30 Hz (33.3 ms cadence); this is
a planning hypothesis, not a requirement that every stage runs every frame.

| Stage              | Proposed allocation | P50        | P90        | P95        | P99        |
| ------------------ | ------------------- | ---------- | ---------- | ---------- | ---------- |
| Camera acquisition | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Preprocessing      | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Detector           | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Tracker            | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Depth              | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Segmentation       | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Ego-motion         | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| World model        | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Trajectory         | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Risk               | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Attention          | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Audio startup      | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |

END_TO_END_ALERT_LATENCY = audio_start_time - source_frame_capture_time

Use timestamps aligned to the same monotonic clock. Source capture is exposure
midpoint; audio start means first actual output, not enqueue time. Account for
capture timestamp uncertainty, buffering, scheduling, queue age and dropped frames.

**Average latency alone is insufficient.** Record P50/P90/P95/P99, maximum,
sample count, warm-up, sustained duration, device temperature, clock alignment error,
battery state and missing/failed samples. Never remove timeouts from the denominator.
Do not sum stage percentiles to claim an end-to-end percentile: measure the actual
critical path, including overlap and queues.

Define allocation and decision criteria before evaluating candidate implementations.
Use mixed-rate scheduling only after measuring freshness and warning lead time.
Core math profiling can start with the opt-in desktop hook in
[guardian-core documentation](../guardian-core.md); it does not establish mobile
performance. No wall-clock timing assertions belong in normal unit tests.

## Camera geometry measurements

| Stage                   | Proposed allocation | P50        | P90        | P95        | P99        |
| ----------------------- | ------------------- | ---------- | ---------- | ---------- | ---------- |
| Pixel to ideal ray      | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Brown inversion and ray | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Camera/device/world ray | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Ray/ground intersection | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |

Use the opt-in GeometryBenchmark described in
[camera geometry](../geometry/CAMERA_MODEL.md) only as a desktop diagnostic.
Measure iterations, failed inversions, allocations/GC and repeated-input reuse
alongside latency. There are no timing-based unit-test gates or validated budgets.

## Temporal and motion costs

| Stage                    | Proposed allocation | P50        | P90        | P95        | P99        |
| ------------------------ | ------------------- | ---------- | ---------- | ---------- | ---------- |
| Sensor ingestion         | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Bounded buffer insertion | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Pose interpolation       | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Filtering                | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Orientation propagation  | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Temporal lookup          | TBD by experiment   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |

These operations are expected to cost much less than neural inference, but that is
an unmeasured hypothesis. SampleBuffer lookup is O(log n), insertion/eviction O(n)
with bounded capacity; there is no sorting on queries. Avoid snapshot allocation in
hot queries. Filters are O(1); stationarity evaluates O(n) supplied window samples.

Opt-in desktop hook after `npm run check:core`:

```powershell
java -cp "packages/guardian-core/target/test-classes;packages/guardian-core/target/classes" dev.sentinel.guardian.TemporalBenchmark
```

The hook warms up, consumes output and reports aggregate insert+lookup timing. It
is not a percentile measurement or validated mobile budget. Profile allocation/GC,
late floods, sustained temperature and 200 Hz workloads on target hardware. No brittle
timing-based assertions are added to tests.

## Desktop laboratory stages

The following Task005 baseline table was unmeasured at creation. No-op timing does
not estimate model cost. Task006C measurements are recorded separately below.

| Stage                       | P50        | P90        | P95        | P99        |
| --------------------------- | ---------- | ---------- | ---------- | ---------- |
| Decode                      | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Pixel conversion            | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Queue delay                 | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Preprocessing               | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Scheduler overhead          | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Model execution placeholder | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Postprocessing              | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Recording                   | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Visualization               | Unmeasured | Unmeasured | Unmeasured | Unmeasured |

Lab processing-clock decode-to-result latency is not source-capture-to-alert latency.
The future critical path must still use an explicitly synchronized observation clock.

## Task006C desktop measurements

CPU/FP32, single ORT thread, PicoDet416 public 36-image diagnostics: P95 loaded-image
to DetectionBatch 1,191 ms and 1,030 ms in two rounds. These are desktop observations,
not targets or mobile estimates. Vendor graph timing includes embedded NMS.
The initial real-video run decoded about 26.6 FPS from 30 FPS media and processed
zero frames because catch-up starved the consumer. It is failed throughput evidence.
The scheduler fix bounds catch-up work; it cannot guarantee processing deadlines or
make slow decoding/inference keep pace. See the Task006C final report for reruns and
result-age/memory measurements. No production latency budget has been validated.

Final corrected 600-second PicoDet replay: 1,459 detector results (~2.43 Hz against
5 Hz requested), zero failures, P95 detector age 291 ms, sampled peak RSS 217,747,456
bytes. Queue depth stayed one. A 60-second 10 Hz request delivered ~6.02 Hz; a
20-second YOLOX 5 Hz smoke delivered 5 Hz. These different durations and uncontrolled
desktop loads must not be conflated into a sustained cross-model performance ranking.
Final still-image reruns measured YOLOX P95 36.5/124.5 ms and PicoDet 266.1/272.6 ms;
earlier slower values remain historical evidence. See the dated report and JSON.

October 18 continuation: YOLOX416 at its frozen .15 threshold ran over 600 seconds
of source, overlapping qualification workloads. It delivered 2,696 detector outputs
(4.49 Hz against 5 Hz requested), zero failures, queue depth one and 206,245,888-byte
peak sampled process-tree RSS. Detector-age P95 was 130.08 ms over the latest 2,048
of 2,696 results. Subsequent 60-second requests delivered 600 results at 10 Hz
(P95 58.16 ms) and 660 results at 15 Hz requested (11 Hz achieved; P95 125.77 ms).
Do not infer sustained 10 Hz, successful 15 Hz, or mobile performance from short runs.
See `results/task006c-reviewed-2026-10-18.md` for the complete qualification evidence.

## Task007 tracking measurements — October 18

Final primary detector plus optimized tracker over 600 seconds: 954 published
processed frames, 837 detector results (1.395 Hz against 5 Hz requested), zero
failures, queue peak one, and two explicit resets across forward observation gaps.
Tracker P50/P90/P95/P99: 10.89/21.10/24.41/33.66 ms. Tracking-result age
P50/P95/P99: 282.40/332.96/934.00 ms. Peak sampled process-tree RSS including JVM:
219,615,232 bytes. Track/history peaks: 64/1,265. RSS sampling began before
initialization and does not establish a steady-state leak rate.

Detector inference and decoding dominate throughput. Per-pair redundant prediction
validation was removed from association; tests and final matrices were rerun.
Short requested 10 Hz runs reached PicoDet 1.10–1.62 Hz and YOLOX 2.73–3.83 Hz;
YOLOX requested 15 Hz reached 2.82 Hz. Desktop load varied and some runs overlapped
verification/benchmarks. These are local observations, not controlled model rankings,
sustained target-rate qualification or mobile guarantees. Real identity-quality
measurements still require human review. See the Task007 report and aggregate CSV.
