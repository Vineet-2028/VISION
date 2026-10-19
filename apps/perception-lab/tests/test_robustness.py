import numpy as np
import pytest

from perception_lab.robustness import stress_image


def test_synthetic_darkening_is_explicit_and_does_not_mutate_source():
    pixels = np.full((2, 3, 3), 100, dtype=np.uint8)
    result = stress_image(pixels, "synthetic-dark-25pct")
    assert np.all(result == 25)
    assert np.all(pixels == 100)
    assert not result.flags.writeable
    assert stress_image(pixels, "original") is pixels


def test_blur_kernel_energy_and_geometry_are_hand_computable():
    pixels = np.zeros((1, 9, 3), dtype=np.uint8)
    pixels[:, 4, :] = 90
    result = stress_image(pixels, "synthetic-horizontal-blur-9px")
    assert result.shape == pixels.shape
    assert np.all(result == 10)
    assert not result.flags.writeable
    with pytest.raises(ValueError):
        stress_image(pixels, "real-world-blur")
