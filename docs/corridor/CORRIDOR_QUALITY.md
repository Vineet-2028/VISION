# Quality and temporal policy

IMPLEMENTED outputs use DEGRADED, UNRELIABLE or UNAVAILABLE. GOOD is a possible future quality, but the prototype does not manufacture it from unvalidated inputs. Reasons distinguish image-only fallback, missing calibration/ground/pose, stale camera evidence and projection unavailability. Heading evidence records original FrameIdentity, age, quality, status and provenance.

Every output timestamp equals WorldState.state_timestamp. No hidden clock or smoothing buffer exists. Metric ground/pose evidence must match the current image identity and calibration; stale-but-non-null pose is not fresh. Exact geometry input quaternions must be finite and unit length. Relative depth is never meters. Metric source uncertainty/validation remains inherited and unvalidated.

Image fallback is a research relevance heuristic. CAMERA_FORWARD and POSE_CAMERA_FORWARD explicitly mean the camera optical axis, not physical walking velocity or torso heading. Fast turns update directly; no old forward corridor persists. Rapid-turn analytical tests establish finite rotations, not useful body-direction accuracy.

Camera/body disagreement, tracking fragmentation, unvalidated depth/semantics, sparse sampling and low inference cadence remain MEDIUM research limitations. None may be hidden by a green/safe label or an invented safety probability. Human semantic review remains deferred; all 96 pages stay DRAFT/UNVERIFIED.
