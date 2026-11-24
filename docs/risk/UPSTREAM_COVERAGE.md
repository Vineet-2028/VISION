# Upstream coverage ceiling

Task014's **5.8% tracker-proxy entry recall** remains explicit in every RiskAssessmentSet and debug overlay. It is not physical hazard recall. Task015 does not retune Task014 geometry.

IMPLEMENTED evaluation separates: upstream entry prediction, risk classification conditional on that prediction, and risk evidence over the same eligible proxy windows. Current occupancy can supply independent evidence even when future prediction misses. This must not be represented as improved Task014 prediction.

The proxy reference already requires an observed tracked WorldEntity and qualifying future same-ID observations. Therefore detector misses and events missing from WorldState are unobservable here. Funnel fields for independently reviewed source events and detector/tracker misses are null, not zero or invented counts. Each measured eligible proxy window is already represented by tracking and WorldState. Counts are windows/hypotheses, not independently deduplicated physical events.

Current corridor occupancy can include bounding-box overlap while the bottom-center point used by the entry proxy remains outside. A current-occupancy classification at that window's start is therefore legitimate evidence with different geometry, not proof that future entry prediction improved. The proxy risk scorecard must retain this distinction.

UNVALIDATED: true end-to-end hazard recall. A reviewed source-event denominator is needed to quantify losses before tracking, followed by matched world/interaction/risk coverage. Task018 should use adjudicated held-out events before final V0 claims.
