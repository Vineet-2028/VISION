"""Deterministic analytical fixture only; never an automatic runtime fallback."""

from math import isfinite

import numpy as np
from numpy.typing import NDArray

from .contracts import ComponentProvenance
from .flow import FramePair, SparseFlowObservation, restore_points
from .geometry import ImageMapping


class SyntheticFlowProvider:
    provenance = ComponentProvenance("synthetic-displacement", "optical_flow", runtime="analytical")

    def __init__(self, dx: float = 0, dy: float = 0) -> None:
        if not isfinite(dx) or not isfinite(dy):
            raise ValueError("Finite displacement required")
        self.displacement = np.array([dx, dy])

    def estimate(
        self, a: NDArray[np.uint8], b: NDArray[np.uint8], pair: FramePair, mapping: ImageMapping
    ) -> SparseFlowObservation:
        if (
            a.shape != b.shape
            or a.ndim != 2
            or mapping.target_dimensions != (a.shape[1], a.shape[0])
        ):
            raise ValueError("Fixture dimensions mismatch")
        x, y = np.meshgrid(
            np.linspace(0.5, a.shape[1] - 0.5, 16), np.linspace(0.5, a.shape[0] - 0.5, 12)
        )
        points = np.column_stack((x.ravel(), y.ravel()))
        return SparseFlowObservation(
            pair,
            restore_points(mapping, points),
            restore_points(mapping, points + self.displacement),
            np.ones(len(points), dtype=np.bool_),
            np.zeros(len(points)),
            self.provenance,
            0,
            0,
        )
