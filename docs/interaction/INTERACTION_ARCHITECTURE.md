# Interaction architecture

IMPLEMENTED: WorldState + CorridorAnalysis + TrajectorySet → InteractionAnalysis. The optional stateless TrajectoryCorridorInteractionAnalyzer runs after prediction in the existing single-owner Pipeline. There is no new worker, inference model, database, network service, persistent identity, queue or entity-pair graph. Each supplied trajectory hypothesis gets a separate forecast; preferred trajectory selection remains a downstream explicit choice. Hypotheses are not independent votes.

InteractionAnalyzer is the replacement protocol. Consumers import interaction_types, not implementation classes. Inputs must share session, source timestamp, schema and world provenance. No wall clock participates in evidence. Unknown entity IDs, invalid units, unordered observations, future observations and unbounded values are rejected. Missing coordinate mappings remain UNKNOWN without discarding the hypothesis.

Runtime is O(N × H × E), with at most512 entities,2048 hypotheses,8 horizons,16 convex polygon edges and3 seconds. No interaction history is retained. A new WorldEntityId starts independent evidence. Typed config is frozen, versioned and rejects unknown fields. Research thresholds are not production safety thresholds.

PLANNED: Task015 consumes all four immutable outputs; Task016 may later consume risk changes. Neither is implemented by Task014. Future ReferenceMotion and a time-varying corridor adapter can replace current reference selection without changing EntityInteractionForecast. The current implementation explicitly uses a frozen corridor and a point path, not full object volume.
