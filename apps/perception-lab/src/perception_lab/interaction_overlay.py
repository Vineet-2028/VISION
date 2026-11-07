"""Bounded neutral debug summary, never user-facing advice."""

import cv2
import numpy as np
from numpy.typing import NDArray

from .interaction_types import InteractionAnalysis


def draw_interactions(pixels: NDArray[np.uint8], result: InteractionAnalysis) -> NDArray[np.uint8]:
    output = pixels.copy()
    height, width = output.shape[:2]
    cv2.rectangle(
        output,
        (4, 40),
        (min(width - 1, 1000), min(height - 1, 68 + 18 * min(8, len(result.entity_interactions)))),
        (25, 25, 25),
        -1,
    )
    cv2.putText(
        output,
        "INTERACTION RESEARCH / physical TTC and CPA unvalidated",
        (8, 55),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (220, 220, 220),
        1,
    )
    for i, r in enumerate(result.entity_interactions[:8]):
        entry = (
            f"{r.predicted_corridor_entry_time_ns / 1e9:.1f}s prediction"
            if r.predicted_corridor_entry_time_ns is not None
            else "--"
        )
        line = f"#{r.entity_id.serial} {r.interaction_type} entry {entry} TTC {r.ttc.status}"
        cv2.putText(
            output, line, (8, 73 + i * 18), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (220, 220, 220), 1
        )
    return output
