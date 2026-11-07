"""Engineering intent panel. No wearer-facing alert wording."""

import cv2
import numpy as np
from numpy.typing import NDArray

from .attention_types import AttentionDecisionSet


def draw_attention(pixels: NDArray[np.uint8], result: AttentionDecisionSet) -> NDArray[np.uint8]:
    output = pixels.copy()
    h, w = output.shape[:2]
    y = max(15, h - 180)
    cv2.rectangle(output, (0, y - 14), (w - 1, h - 1), (25, 25, 25), -1)
    lines = ["ATTENTION PROTOTYPE / upstream proxy recall 5.8% / NO AUDIO"]
    for d in (*result.selected, *(s.decision for s in result.suppressed[:5])):
        identity = d.entity_id.serial if d.entity_id else "scene"
        lines.append(f"#{identity} {d.source_risk_level}: {d.decision} {'/'.join(d.reason_codes)}")
    for i, line in enumerate(lines):
        cv2.putText(
            output, line, (6, y + i * 22), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (230, 230, 230), 1
        )
    return output
