"""Engineering-only explanation panel; no user-facing advice."""

import cv2
import numpy as np
from numpy.typing import NDArray

from .risk_types import RiskAssessmentSet


def draw_risk(pixels: NDArray[np.uint8], result: RiskAssessmentSet) -> NDArray[np.uint8]:
    output = pixels.copy()
    h, w = output.shape[:2]
    y = max(15, h - 185)
    cv2.rectangle(output, (0, y - 14), (w - 1, h - 1), (25, 25, 25), -1)
    lines = ["RISK PROTOTYPE / TTC unvalidated / upstream proxy recall 5.8%"]
    for a in result.assessments[:6]:
        why = ", ".join(f.code for f in a.risk_factors) or "INSUFFICIENT_EVIDENCE"
        lines.append(f"#{a.entity_id.serial} {a.risk_level} / {a.evidence_quality}: {why}")
    for i, line in enumerate(lines):
        cv2.putText(
            output, line, (6, y + i * 22), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (230, 230, 230), 1
        )
    return output
