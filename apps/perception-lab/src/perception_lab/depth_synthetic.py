"""Deterministic analytical provider; never a substitute for model evaluation."""

from time import perf_counter_ns

import numpy as np

from .contracts import ComponentProvenance, FrameIdentity
from .depth import DepthAxis, DepthDirection, DepthFrame, DepthKind, DepthRepresentation
from .preprocessing import PreparedImage


class SyntheticDepthProvider:
    provenance = ComponentProvenance("synthetic-depth", "depth", "synthetic-plane", "1", "numpy")

    def __init__(self, value: float = 5.0, gradient: float = 0.0) -> None:
        if not np.isfinite(value) or value <= 0 or not np.isfinite(gradient):
            raise ValueError("Invalid synthetic plane")
        self.value, self.gradient = value, gradient

    def estimate_depth(self, image: PreparedImage, identity: FrameIdentity) -> DepthFrame:
        start = perf_counter_ns()
        width, height = image.descriptor.width, image.descriptor.height
        values = np.broadcast_to(
            self.value + self.gradient * np.arange(width, dtype=np.float32), (height, width)
        )
        return DepthFrame(
            identity,
            DepthRepresentation(
                DepthKind.METRIC, DepthDirection.LARGER_IS_FARTHER, DepthAxis.CAMERA_Z
            ),
            values,
            np.ones(values.shape, dtype=np.bool_),
            image.mapping,
            self.provenance,
            start,
            perf_counter_ns(),
        )
