"""Opt-in debug rendering, outside the geometry hot path. Neutral evidence labels."""

import cv2
import numpy as np
from numpy.typing import NDArray

from .corridor_types import CorridorAnalysis
from .world_types import WorldState


def draw_corridor(
    pixels: NDArray[np.uint8], state: WorldState, analysis: CorridorAnalysis
) -> NDArray[np.uint8]:
    if analysis.session_id != state.session_id or analysis.state_timestamp != state.state_timestamp:
        raise ValueError("Overlay state mismatch")
    output = pixels.copy()  # Debug only; never mutate the source buffer.
    image = state.image_geometry
    if image is None:
        return output
    sx, sy = output.shape[1] / image.width, output.shape[0] / image.height
    polygon = np.asarray(
        [(round(x * sx), round(y * sy)) for x, y in analysis.corridor.image_polygon], dtype=np.int32
    )
    if len(polygon) >= 3:
        cv2.polylines(output, [polygon], True, (100, 190, 240), 2)
    colors = {
        "INSIDE": (70, 190, 230),
        "NEAR_BOUNDARY": (190, 140, 220),
        "INTERSECTS": (140, 180, 230),
        "OUTSIDE": (160, 160, 160),
        "UNKNOWN": (220, 220, 220),
    }
    for entity, relation in zip(state.entities, analysis.entity_relations, strict=True):
        box = entity.image_geometry
        x, y = round(box.x1 * sx), round(box.y1 * sy)
        cv2.rectangle(
            output,
            (x, y),
            (round(box.x2 * sx), round(box.y2 * sy)),
            colors[relation.relation.value],
            1,
        )
        cv2.putText(
            output,
            f"#{entity.entity_id.serial} {relation.relation.value}",
            (max(0, x), max(12, y)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            colors[relation.relation.value],
            1,
        )
    for x, y, flags in state.surface_state.samples:
        if analysis.surface_evidence.sample_count:
            color = (
                (190, 190, 190)
                if flags & 1 or flags == 0
                else (150, 120, 190)
                if flags & (8 | 16)
                else (100, 160, 190)
            )
            cv2.circle(output, (round(x * sx), round(y * sy)), 1, color, -1)
    cv2.putText(
        output,
        f"CORRIDOR | {analysis.corridor.mode.value} | UNVERIFIED",
        (8, 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (230, 230, 230),
        1,
    )
    cv2.putText(
        output,
        f"Unknown sampled fraction {analysis.surface_evidence.unknown_fraction:.2f}"
        "; unseen UNKNOWN",
        (8, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (230, 230, 230),
        1,
    )
    return output
