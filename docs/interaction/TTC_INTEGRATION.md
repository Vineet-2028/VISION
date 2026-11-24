# TTC integration

IMPLEMENTED: CoreGeometry.relative_motion delegates relativePosition, relativeVelocity, closingSpeed and radialTtc to guardian-core Motion. Python contains no TTC formula. Guardian uses meters and meters/second in one explicit LOCAL_WORLD frame. Positive closing speed means decreasing radial separation. A configured minimum closing speed can further restrict Guardian's numerical threshold, never relax it.

TimeToContactCandidate retains status, seconds where computable, closing speed, reference, physical validity, quality, source trajectory IDs, assumptions and provenance. Statuses distinguish invalid units, disabled research, missing reference, insufficient position/velocity, near-zero separation, non-closing and outside horizon. No Infinity sentinel or negative TTC is emitted. A mathematically finite value beyond the supplied horizon is diagnostic OUTSIDE_PREDICTION_HORIZON, not an extended trajectory.

Research calculation requires explicit research_metric, compatible metric world evidence and a reference. static_user_reference is independently opt-in. Its origin is the current supplied device/world pose, with zero assumed velocity, STATIC_USER_ASSUMPTION and RESEARCH_ONLY. It is not a validated moving-user TTC. Relative depth and image/bearing velocity cannot enter this path. Current real footage has no eligible metric/user-motion evidence, so physical estimates remain unavailable.

Finite radial TTC is not collision proof: a side pass can have finite TTC and nonzero CPA. Predicted corridor entry is a separate field and is never copied into TTC. Optical-expansion/tau TTC is deferred.
