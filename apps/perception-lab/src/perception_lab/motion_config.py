"""Bounded versioned CPU motion configuration; no hidden safety thresholds."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class MotionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)
    schema_version: Literal[1] = 1
    flow_provider: Literal["lk", "dis"] = "lk"
    max_features: Annotated[int, Field(ge=16, le=2048)] = 400
    max_width: Annotated[int, Field(ge=64, le=1024)] = 640
    max_gap_ns: Annotated[int, Field(gt=0, le=5_000_000_000)] = 500_000_000
    quality_level: Annotated[float, Field(gt=0, le=1)] = 0.01
    min_distance: Annotated[int, Field(ge=2, le=64)] = 8
    window: Annotated[int, Field(ge=5, le=51)] = 21
    pyramid_levels: Annotated[int, Field(ge=0, le=5)] = 3
    fb_threshold: Annotated[float, Field(gt=0, le=10)] = 1.5
    dis_preset: Literal[0, 1, 2] = 1
    estimator: Literal["visual", "none"] = "visual"
    dynamic_masking: bool = True
    minimum_features: Annotated[int, Field(ge=8, le=256)] = 16
    minimum_coverage: Annotated[float, Field(gt=0, le=1)] = 0.375
    minimum_inlier_ratio: Annotated[float, Field(gt=0, le=1)] = 0.6
    ransac_iterations: Annotated[int, Field(ge=16, le=2000)] = 200
    ransac_pixels: Annotated[float, Field(gt=0, le=10)] = 1.5
    seed: Annotated[int, Field(ge=0, le=2**31 - 1)] = 9
