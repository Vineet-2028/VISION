# CPA integration

IMPLEMENTED: Guardian Motion.closestApproach remains the authoritative future CPA. An additive signedClosestApproachSeconds query retains past mathematical minimizers while preserving the old future-only API. closestApproach now reuses that query; no production equation is duplicated in Python.

ClosestApproachCandidate retains signed time, future distance when defined, current estimated separation, reference, quality, validity, source IDs, assumptions and provenance. ZERO_RELATIVE_VELOCITY means no unique minimum time. PAST_CLOSEST_APPROACH retains negative time without clamping. OUTSIDE_PREDICTION_HORIZON flags values outside the available Task013 samples. Current separation is not described as measured physical truth.

Synthetic head-on and side-pass fixtures exercise the actual JPype bridge and exact expected geometry; these validate mathematics only. Linear radial TTC and piecewise corridor evidence need not agree. Bounded diagnostics retain finite TTC without corridor intersection and corridor intersection with unavailable TTC. These are evidence differences, not risk resolutions.
