"""Opt-in neutral image prediction paths. No in-place pixel edits or safety colors."""

import cv2
import numpy as np
from numpy.typing import NDArray

from .trajectory_types import TrajectoryDomain, TrajectorySet


def draw_trajectories(pixels: NDArray[np.uint8], result: TrajectorySet) -> NDArray[np.uint8]:
    output = pixels.copy()
    height, width = output.shape[:2]
    entries = {
        r.trajectory_id: r.predicted_corridor_entry_time_ns for r in result.corridor_relations
    }
    for t in result.trajectories:
        if t.coordinate_space != TrajectoryDomain.IMAGE or t.motion_basis != "OBSERVED_HISTORY":
            continue

        def pixel(p: tuple[float, ...]) -> tuple[int, int]:
            # Bound OpenCV integer conversion; draw clips to visible image.
            return round(max(-width * 2, min(width * 3, p[0]))), round(
                max(-height * 2, min(height * 3, p[1]))
            )

        points = [pixel(t.origin), *(pixel(s.position) for s in t.samples)]
        cv2.polylines(output, [np.array(points, dtype=np.int32)], False, (180, 160, 230), 1)
        for sample, point in zip(t.samples, points[1:], strict=True):
            cv2.circle(
                output,
                point,
                min(max(width, height), max(1, round(sample.envelope_radius))),
                (120, 150, 170),
                1,
            )
        entry = entries.get(t.trajectory_id)
        label = f"prediction #{t.entity_id.serial} {t.model}"
        if entry is not None:
            label += f" entry {entry / 1e9:.2f}s"
        cv2.putText(output, label, points[0], cv2.FONT_HERSHEY_SIMPLEX, 0.35, (220, 220, 220), 1)
    cv2.putText(
        output,
        "PREDICTION / UNVALIDATED / frozen corridor",
        (8, max(12, height - 12)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (220, 220, 220),
        1,
    )
    return output
