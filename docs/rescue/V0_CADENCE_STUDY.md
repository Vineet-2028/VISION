# V0 cadence study

`tools/rescue_cadence.py` ran nine sequential 15-second pilots against the same
source, model artifacts and reference conventions. Requested rates are eligibility
rates, not guaranteed completed inferences. Each result retains its own config,
counts, latency distribution, worker counters, rejection counts and RSS samples.

| Profile                | Detector / depth / semantic / flow Hz       | Updates | Publication age P95 ms | Interval P95 ms |
| ---------------------- | ------------------------------------------- | ------: | ---------------------: | --------------: |
| detector-2             | 2 / 1 / 1 / 5                               |      72 |                 696.71 |          642.84 |
| detector-5             | 5 / 1 / 1 / 5                               |      35 |                 762.68 |          662.46 |
| detector-10            | 10 / 1 / 1 / 5                              |      59 |                 630.31 |          471.23 |
| depth-2                | 5 / 2 / 1 / 5                               |     200 |                 265.14 |          247.97 |
| depth-5                | 5 / 5 / 1 / 5                               |     200 |                 244.42 |          248.63 |
| semantic-half          | 5 / 1 / 0.5 / 5                             |     241 |                 210.30 |          169.59 |
| semantic-2             | 5 / 1 / 2 / 5                               |      57 |                 776.43 |          643.08 |
| image-space-degraded   | 5 / unavailable / 0.5 / 5                   |      40 |                 604.18 |          533.93 |
| detector-only-degraded | 5 / unavailable / unavailable / unavailable |      44 |                 476.97 |          400.87 |

All pilots completed with zero processing failures and zero gap resets. These
short, fixed-order trials have substantial host/load/warm-up confounding. Increasing
the requested depth rate did not establish that depth became faster: the bounded
worker replaces work when overloaded. Do not interpret these as causal speedups,
production cadence recommendations, or substitutes for the full run.

The semantic-half profile was selected for a sustained trial because its pilot
retained all configured providers. The image-space profiles are explicit degraded
alternatives, not silently equivalent measurements. Final readiness and selected
configuration depend on the sustained evidence in the rescue results report.

The sustained all-provider trial (`realtime-03`) processed 1,050 updates in the
600-second window, below the 2 Hz target. Its measurement completion guard also
failed because it used the last delivered frame instead of the acquisition end
boundary; the failed artifact is preserved. A subsequent run (`realtime-04`) with
detector requested at 5 Hz and depth/flow/semantics explicitly unavailable
completed 1,804 updates in 600.636 seconds (3.003 Hz). Publication age P95 was
687.945 ms. This was the initial **degraded image-space engineering profile**,
not qualification of the all-provider profile or a production cadence default.

The pilot matrix was executed before the additional post-detector expiry recheck
and shutdown-error regression fix. Final qualification uses the stricter code.

After GPU qualification, `realtime-05-gpu` retained all providers and completed
2,447 updates in 600.509 pipeline seconds (4.075 Hz), publication-age P95
554.441 ms, zero failures/gap resets, and 59 non-expired texts. CPU depth averaged
4.930 seconds per job and its minimum output age already exceeded admission limits.

The final `realtime-06-gpu-no-depth` therefore disables depth explicitly, retaining
CUDA FP32 detection at requested 5 Hz, CUDA segmentation at 0.5 Hz, and CPU flow
at 5 Hz. It completed 2,641 updates in 600.404 seconds (4.399 Hz), zero failures,
one gap reset, 567.211 ms publication-age P95 and 60 non-expired texts. Its linked
central-event delivery was 2/188 versus 0/188 in the all-provider GPU trial. These
are separate outcomes, not a controlled causal estimate. Neither 5 Hz nor 500 ms
P95 stretch target was met; the minimum engineering goals were met.
