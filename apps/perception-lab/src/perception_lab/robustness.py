"""Controlled pixel stress experiments; never labeled real low-light or camera motion."""

import numpy as np
from numpy.typing import NDArray


def stress_image(pixels: NDArray[np.uint8], condition: str) -> NDArray[np.uint8]:
    if pixels.dtype != np.uint8 or pixels.ndim != 3 or pixels.shape[2] != 3:
        raise ValueError("Expected RGB uint8 image")
    if condition == "original":
        return pixels
    if condition == "synthetic-dark-25pct":
        result = np.floor(pixels.astype(np.float32) * 0.25).astype(np.uint8)
    elif condition == "synthetic-horizontal-blur-9px":
        # Explicit nine-tap box PSF, edge extension, no resize or coordinate shift.
        padded = np.pad(pixels, ((0, 0), (4, 4), (0, 0)), mode="edge")
        total = np.zeros(pixels.shape, dtype=np.float32)
        for offset in range(9):
            total += padded[:, offset : offset + pixels.shape[1], :]
        result = np.floor(total / 9).astype(np.uint8)
    else:
        raise ValueError("Unknown stress condition")
    result.flags.writeable = False
    return result
