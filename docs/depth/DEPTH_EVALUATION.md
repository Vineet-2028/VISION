# Depth evaluation

Keep evidence levels separate:

- A: deterministic analytical geometry/association tests.
- B: public metric ground truth, optional and currently unavailable.
- C: user-owned RGB qualitative/temporal diagnostics; no metric ground truth.
- D: calibrated ground-plane consistency, currently unavailable for real footage.

tools/depth_benchmark.py compares two Small checkpoints at two input sizes and five region strategies on a bounded set. It verifies selected image hashes and records model hashes, timings, RSS snapshots, sample validity and dispersion. Its annotations inherit prototype Task007 limitations. Scenario labels remain UNKNOWN unless separately reviewed; there is no established low-light/crowd/thin-object accuracy score.

Percentiles from a small sample are descriptive, include first inference, and are not sustained latency guarantees. Concurrent desktop work confounds cross-model ranking. A ten-minute replay measures bounded processing behavior, not physical ranging accuracy. RSS is sampled, not a proof of leak freedom.

Temporal changes can reflect camera/object motion, relative-scale drift or identity errors; do not label variation as distance error. Relative and metric numeric outputs cannot be subtracted meaningfully; compare ordering or explicitly aligned outputs. No model fusion is implemented.

Optional future metric benchmark must document depth semantics, units, alignment and dataset rights before calculating AbsRel, SqRel, RMSE, RMSE-log and delta thresholds. Relative outputs require ordering/alignment metrics and cannot be treated as meters.
