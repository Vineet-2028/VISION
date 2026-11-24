# Quality and validity

IMPLEMENTED: all prototype output is at best DEGRADED. Predicted tracks, low input quality, rejected outliers, high fit residual, and unreliable scene/entity evidence yield UNRELIABLE. Missing/freshness-failing domains appear in explicit unavailable diagnostics. Longer horizons beyond1 second are UNRELIABLE. No new calibrated probability is invented.

History must be strictly increasing, causal, source/clock-consistent and session-local. Future observations and mismatched sessions are rejected. Large observation gaps reset retained history. Source age is measured against the provided WorldState timestamp, not wall clock; consumers must separately reject an old entire state against their synchronized time.

UNVALIDATED: physical trajectories, depth, camera compensation, identity continuity, semantic labels, collision and production safety. No category-derived speed, inferred body motion or semantic dependency is introduced.
