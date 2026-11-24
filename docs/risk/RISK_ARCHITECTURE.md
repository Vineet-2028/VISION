# Risk engine architecture

IMPLEMENTED: an optional single-thread-owned `RiskEngine.assess` consumes immutable WorldState, CorridorAnalysis, TrajectorySet and InteractionAnalysis. RuleBasedRiskEngine publishes immutable RiskAssessmentSet schema 1. Pipeline recording schema 10 adds the result. No geometry, TTC/CPA equations, neural inference, upstream mutation, alert queue or navigation instructions are added.

Assessment is O(entities + hypotheses); fixed five-level ranking buckets preserve producer order for ties. Limits are 512 entities and 2048 hypotheses. History stores one timestamp/level/quality per current entity, is pruned by source time, and resets on session change or pipeline close. Disappeared IDs immediately leave history. Inputs with backwards time or duplicate identities are rejected. Misaligned optional sources become unavailable, not fresh observations.

PROVISIONAL: rule thresholds express research relevance, not hazard probability. A weighted implementation is explicitly rejected for V1: no independent risk labels justify extra weights, and summing correlated hypotheses could double-count one interaction. `research_score` remains null. An injected protocol wrapper is tested; future alternative engines must pass the same ordering, validity and expiry tests.

PLANNED: Task016 consumes level, trend, quality, reasons, identity and validity deadline. It owns novelty, suppression and interruption. Task017 owns presentation. Neither is implemented here.
