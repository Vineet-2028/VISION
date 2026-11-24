# Alpha V1.1 release decision

2026-11-18 — candidate branch `codex/alpha-v1-1-release-closure`.

**HOLD. Alpha V1.1 is not promoted. No public deployment.**

| Gate                                | Decision                                                                   |
| ----------------------------------- | -------------------------------------------------------------------------- |
| DIAGNOSTIC_SOFTWARE_FUNCTIONAL      | PARTIAL — functional checks exist; final changed-tree verification pending |
| SECURITY_CLEARED                    | NO — SECURITY_BLOCKER_EXTERNAL_UNRESOLVED                                  |
| READY_FOR_CONTROLLED_FIELD_CAPTURE  | NO — release security hold; physical path unverified                       |
| REAL_PHONE_FIELD_PATH_VERIFIED      | NO — BLOCKED_NO_DEVICE                                                     |
| REAL_FIELD_ROOT_CAUSE_CONFIRMED     | NO — original incident unrecorded                                          |
| PERCEPTION_IMPROVEMENT_DEMONSTRATED | NO — independent reference cases absent                                    |
| ALPHA_V1_1_PROMOTED                 | NO                                                                         |
| PUBLIC_DEPLOYMENT_READY             | NO                                                                         |

The completed GPU evidence remains valid for the unchanged engine/model profile.
Changes here concern offline import, private viewer, operator response handling,
and Android capture usability. No perception threshold, class naming policy,
tracking/risk behavior, freshness, or memory guard was relaxed.

See [final engineering report](../research/results/VISION_ALPHA_V1_1_FINAL.md),
[dependency decision](../security/VISION_DEPENDENCY_ADVISORY_STATUS.md),
[object analysis](../research/VISION_OBJECT_ROOT_CAUSE_ANALYSIS.md), and
[semantic analysis](../research/VISION_SEMANTIC_ROOT_CAUSE_ANALYSIS.md).

Next required evidence: legitimate dependency remediation and full verification,
then consented physical Android capture/export/TTS checks and independently labeled
matched field cases. A physical callback is not an acoustic earbud measurement.
Do not interpret missing data or a checked review box as human validation.

Explore Mode remains POST_V1_1_FEATURE. Task019, cloud training and model swapping
were not started. Unsupervised mobility safety is not validated.
