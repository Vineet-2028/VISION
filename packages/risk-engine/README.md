# Risk engine

Task015's Python prototype lives in `apps/perception-lab/src/perception_lab/risk.py`
with immutable contracts in `risk_types.py`. This directory reserves a future
portable implementation boundary, not a duplicate runtime.

The current rule baseline produces explainable relevance and separate quality,
not probabilities or alerts. Missing evidence is UNDETERMINED. See `docs/risk`.
