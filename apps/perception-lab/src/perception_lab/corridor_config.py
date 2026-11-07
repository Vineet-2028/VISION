"""Research geometry settings, never body dimensions or safety thresholds."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CorridorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)
    schema_version: Literal[1] = 1
    mode: Literal["AUTO", "IMAGE"] = "AUTO"
    near_m: Annotated[float, Field(ge=0.05, le=5)] = 0.5
    far_m: Annotated[float, Field(gt=0.05, le=30)] = 5.0
    near_half_width_m: Annotated[float, Field(ge=0.05, le=5)] = 0.45
    far_half_width_m: Annotated[float, Field(ge=0.05, le=10)] = 0.9
    expansion_m: Annotated[float, Field(ge=0, le=2)] = 0.0
    boundary_m: Annotated[float, Field(ge=0, le=2)] = 0.1
    generic_ground_tolerance_m: Annotated[float, Field(ge=0, le=0.5)] = 0.1
    image_top: Annotated[float, Field(ge=0, lt=0.95)] = 0.45
    image_bottom_half_width: Annotated[float, Field(gt=0, le=0.5)] = 0.3
    image_top_half_width: Annotated[float, Field(gt=0, le=0.5)] = 0.12
    image_boundary_fraction: Annotated[float, Field(ge=0, le=0.1)] = 0.015
    fresh_ns: Annotated[int, Field(ge=1, le=5_000_000_000)] = 500_000_000
    surface_fresh_ns: Annotated[int, Field(ge=1, le=5_000_000_000)] = 1_000_000_000

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.near_m >= self.far_m:
            raise ValueError("Near distance must precede far distance")
        return self
