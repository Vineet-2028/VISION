# Interaction evaluation

IMPLEMENTED synthetic tests: known entry/exit/minimum distance, grazing, parallel miss, static inside, re-entry, nominal/envelope distinction, head-on/side-pass/past/zero-speed Guardian cases, horizon enforcement, frame/session/clock rejection, immutable deterministic results, relative depth rejection, reference replacement and recorder integration.

MEASURED results are in the dated Task014 completion report and JSON. tools/interaction_benchmark.py measures isolated computation, bridge calls, bounded JSON serialization samples and whole-pipeline cadence. It does not run a new ML model.

Real retrospective evaluation freezes the prediction-time corridor and forecasts, samples prediction windows every250ms, and compares later observed same-WorldEntityId bottom centers in that frozen image polygon. Current truth starts at the actual observed box, not the fitted prediction origin. Windows start only for currently observed points outside the corridor. All later observations remain causal and never change published predictions. Piecewise interpolation between observed tracker points supplies a proxy entry time, not independent ground truth.

Report TP/FP/FN/TN, entry precision/recall, matched timing MAE and minimum-distance MAE in pixels. Only windows with <=250ms (200ms detector cadence plus tolerance) observation gaps and final observation within100ms of the horizon qualify; fragmented/incomplete identities are censored, not counted as misses or successes. Pending queue capacity4096, overflow and end-censoring are explicit. An overflowing run cannot qualify comparisons. No claimed physical TTC/CPA or collision accuracy.

UNVALIDATED: independently reviewed pedestrian/bicycle/vehicle/crowd/small-object/high-motion strata. Class occurrence counts are not scenario annotations. Future evaluation must use held-out reviewed trajectories and motion strata; development footage has tracker-reference bias. Low-light and body-motion qualification remain planned.
