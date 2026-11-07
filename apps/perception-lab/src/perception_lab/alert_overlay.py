"""Engineering-only text panel, distinct from actual audio delivery."""

import cv2
import numpy as np
from numpy.typing import NDArray

from .alert_types import AlertOutputSet


def draw_alerts(pixels: NDArray[np.uint8], result: AlertOutputSet) -> NDArray[np.uint8]:
    output = pixels.copy()
    y = 24
    lines = [f"ALERTS: {result.mode} / PROTOTYPE / TEXT ONLY"]
    for row in result.outputs[:2]:
        text = row.presentation.speech_text if row.presentation else row.reason
        age = row.presentation.source_age_ns if row.presentation else None
        lines.append(f"{row.status}: {text} / source age ns: {age}")
    for line in lines:
        cv2.putText(output, line, (6, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        y += 22
    return output
