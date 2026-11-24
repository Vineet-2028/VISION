# Physical validity and reference ownership

UNVALIDATED: current real depth is relative/unvalidated, metric ego translation and user motion are not validated, physical trajectory accuracy is not established, and semantic human review remains deferred (96 pages UNVERIFIED). Task014 does not alter those records.

IMPLEMENTED: exact frame/session/timestamp gates, metric depth-kind checks, fresh pose/track source joins, domain validity and research opt-ins. No pixel quantity is labeled meters. Static-user diagnostics remain research-only and cannot masquerade as real moving-user TTC/CPA. Even a supplied ReferenceMotion marked validated does not promote an unvalidated object trajectory.

PLANNED: future synchronized stereo/ToF/LiDAR/VIO adapters can supply stronger evidence through the existing world/trajectory/reference contracts. A validated user trajectory adapter supplies position and velocity at the matching source timestamp, frame, units and provenance through ReferenceMotion. Extending the physical authorization policy and a moving-corridor provider would not require replacing forecast consumers or duplicating equations.

Ground-truth protocol: independently measure object and camera/user trajectories with calibrated markers, external range or motion capture; synchronize clocks; record reference uncertainty; hold out actors/scenes; evaluate misses, side passes, near-zero and receding cases at each horizon. Predeclare acceptable timing/distance errors and censoring rules. Physical collision, risk and production safety require separate system validation beyond these mathematics.
