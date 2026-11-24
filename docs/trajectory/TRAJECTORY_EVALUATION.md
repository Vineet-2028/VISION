# Evaluation protocol

IMPLEMENTED: tools/trajectory_benchmark.py creates deterministic stationary, linear, vertical, diagonal, acceleration, jitter, outlier and irregular-time fixtures. It compares CP, last-two CV and window CV using per-horizon errors, ADE and final-horizon FDE in pixels. Guardian-backed3D tests independently exercise world axes, metric candidate gates and extrapolation. Synthetic math does not validate sensors.

Real retrospective evaluation freezes predictions before future observations arrive, matches the same WorldEntityId at or after target within100ms, and records offset/error/count. Evaluation samples a prediction set every250ms while scoring against every observed frame. Its bounded pending queue holds at most65536 samples; expiry, overflow and end-censored counts are reported. A run with overflow cannot qualify model comparisons. These are future TRACKER proxies with identity bias, not independent reviewed truth. Residual-versus-raw comparison is explicitly a coordinate-mismatch diagnostic, not a fair stabilized-view accuracy score. No online parameter changes occur.

No current footage provides independent physical trajectory truth. Crowds, small objects, low light and high-motion strata require reviewed labels before claims. Existing capture is development evidence, not separate qualification data. Future data loop: frozen state/prediction -> later observed reference -> error/hard-case registry -> reviewed offline qualification; no cloud upload/self-training implemented.

MEASURED results and limitations belong in the Task013 completion report. Never replace unavailable metrics with zero.
