# Task013 trajectory architecture

IMPLEMENTED: stateless TrajectoryPredictor.predict(WorldState, optional CorridorAnalysis) produces immutable TrajectorySet schema1. Pipeline invokes it after each WorldState/corridor update, with no worker, new inference model or feedback into tracking/world observations. Recording schema8 adds compact trajectories; trajectory-disabled older records keep their versions.

World EntityHistory additively retains Guardian-derived bearing and exact depth/pose world candidates with source evidence. No latest-pose substitution. Histories remain bounded by the world model; predictor reads at most32 observations per entity and accepts at most512 entities. No session cache, whole-session scan, pairwise entity matrix or model runtime dependency exists.

Preference order is world research, bearing, then image, explicitly a representation preference rather than accuracy ranking. All available domains remain published. Residual-flow hypotheses are separate stabilized-view research outputs and never preferred over raw trajectories.

PLANNED: a learned predictor may implement the same protocol only after controlled qualification. Body/user trajectory, destination, social intent, maps, risk, warnings and cloud systems are outside this task. Task014 receives WorldState + CorridorAnalysis + TrajectorySet; it must check session/time/frame/units/physical status before relative approach or interaction math. Task015 can consume that evidence without importing predictor implementation. Neither task is implemented here.

Portability: bounded tuples and small deterministic fits can move to Java/Kotlin. Guardian already owns metric nominal extrapolation; Python owns research fit/selection and image-domain policy. No heavy dependency was added.
