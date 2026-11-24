import numpy as np
import pytest

from perception_lab.camera_view_quality import (
    CameraViewQualityEstimator,
    ViewQualityConfig,
    ViewStatus,
)
from perception_lab.contracts import Frame, FrameIdentity, PixelFormat, TimingProvenance


def evaluate(pixels, pixel_format=PixelFormat.GRAY, config=None):
    identity = FrameIdentity("view-fixture", 1, 100, TimingProvenance.SYNTHETIC)
    frame = Frame(identity, pixels, pixel_format, 1, 2)
    result = CameraViewQualityEstimator(config or ViewQualityConfig()).estimate(frame)
    assert result.identity == identity
    return result


@pytest.mark.parametrize("value,reason", [(0, "TOO_DARK"), (255, "OVEREXPOSED")])
def test_extreme_exposure_blocks_scene_reasoning(value, reason):
    result = evaluate(np.full((64, 64, 1), value, dtype=np.uint8))
    assert result.status == ViewStatus.UNUSABLE
    assert reason in result.reasons
    assert not result.permits_scene_reasoning
    assert "OCCLUDED" not in result.reasons


def test_plain_wall_is_degraded_without_fabricating_occlusion():
    result = evaluate(np.full((64, 64, 1), 127, dtype=np.uint8))
    assert result.status == ViewStatus.DEGRADED
    assert result.reasons == ("INSUFFICIENT_SCENE",)
    assert "OCCLUSION_LIKE_UNIFORMITY" in result.indicators
    assert result.diagnostics.entropy_bits == 0


def test_textured_image_is_bounded_and_rgb_bgr_equivalent():
    pixels = np.random.default_rng(42).integers(20, 230, (720, 1280, 3), dtype=np.uint8)
    rgb = evaluate(pixels, PixelFormat.RGB)
    bgr = evaluate(pixels[:, :, ::-1].copy(), PixelFormat.BGR)
    assert rgb.status == ViewStatus.GOOD
    assert rgb.diagnostics.sampled_pixels <= 128**2
    assert rgb.diagnostics.mean_luminance == pytest.approx(bgr.diagnostics.mean_luminance)
    assert rgb.reasons == bgr.reasons


def test_smooth_gradient_reports_low_detail_not_proven_blur():
    pixels = np.tile(np.arange(64, dtype=np.uint8) * 2 + 40, (64, 1))[:, :, None]
    result = evaluate(pixels)
    assert result.status == ViewStatus.DEGRADED
    assert "LOW_SPATIAL_DETAIL" in result.indicators
    assert "SEVERE_BLUR" not in result.reasons


@pytest.mark.parametrize(
    "shape,kind", [((2, 3, 1), PixelFormat.GRAY), ((32, 32, 4), PixelFormat.RGBA)]
)
def test_unsupported_or_small_images_are_unknown(shape, kind):
    result = evaluate(np.zeros(shape, dtype=np.uint8), kind)
    assert result.status == ViewStatus.UNKNOWN
    assert not result.permits_scene_reasoning and result.diagnostics is None


def test_threshold_configuration_is_validated_and_provenance_changes():
    with pytest.raises(ValueError):
        ViewQualityConfig(degraded_fraction=0.99)
    with pytest.raises(ValueError):
        ViewQualityConfig(dark_pixel=float("nan"))
    a = CameraViewQualityEstimator(ViewQualityConfig())
    b = CameraViewQualityEstimator(ViewQualityConfig(sample_side=64))
    assert a.configuration_hash != b.configuration_hash


def test_directional_pattern_is_indicator_not_claim_of_motion():
    stripes = np.tile((np.arange(64) % 2 * 180 + 30).astype(np.uint8), (64, 1))[:, :, None]
    result = evaluate(stripes)
    assert "DIRECTIONAL_TEXTURE_OR_MOTION_SMEAR" in result.indicators
    assert "FACING_GROUND" not in result.reasons and "FACING_SKY" not in result.reasons
