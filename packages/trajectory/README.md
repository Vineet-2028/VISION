# Trajectory

Reserved for temporal association and trajectory prediction. Raw kinematics and
constant-velocity TTC/CPA utilities live in [guardian-core](../guardian-core/README.md).
No tracker, filter or predictive orchestration is implemented in this directory.

Task013's prototype implementation lives in `apps/perception-lab/src/perception_lab/trajectory*.py`,
with immutable contracts consumed downstream of WorldState. Guardian owns nominal metric prediction;
the lab owns bounded fitting, research model selection and image-domain hypotheses. See the
[trajectory architecture](../../docs/trajectory/TRAJECTORY_ARCHITECTURE.md). This package remains a
portability boundary; do not duplicate the lab implementation here before a runtime needs it.
