# Explainable factors

IMPLEMENTED supporting factors: current corridor occupancy, predicted corridor entry with its source-time offset, and possible envelope intersection. Reducing factors: outside the modeled corridor and receding from it. Factors carry code, effect, source and compact value. Every level retains reason codes, source ages, configuration hash and provenance.

TTC/CPA are diagnostic only. Minimum corridor distance, class, draft semantics and raw confidence are not weighted in V1: their different units and calibration do not justify a shared numeric sum. Approach alone cannot imply an entry or raise an outside object to HIGH. Static or stable in-corridor evidence is retained when supplied by Task014; no new velocity estimate is computed.

Multiple forecasts are alternative hypotheses, not independent votes. One usable positive hypothesis may support relevance; LOW requires every usable hypothesis to indicate no intersection. Quality-gated/unavailable hypotheses are disclosed. No research score or calibrated probability is produced.
