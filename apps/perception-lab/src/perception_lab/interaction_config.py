"""Research geometry settings, never safety thresholds."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class InteractionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)
    schema_version: Literal[1] = 1
    horizon_ns: Annotated[int, Field(gt=0, le=3_000_000_000)] = 3_000_000_000
    max_age_ns: Annotated[int, Field(gt=0, le=3_000_000_000)] = 500_000_000
    near_boundary_pixels: Annotated[float, Field(ge=0, le=100)] = 2.0
    near_boundary_meters: Annotated[float, Field(ge=0, le=10)] = 0.1
    bearing_tolerance_radians: Annotated[float, Field(ge=0, le=1)] = 0.01
    minimum_closing_speed_mps: Annotated[float, Field(ge=0, le=10)] = 0.001
    research_metric: bool = False
    static_user_reference: bool = False
    interpolation: Literal["PIECEWISE_LINEAR"] = "PIECEWISE_LINEAR"
    cpa_horizon_policy: Literal["FLAG_OUTSIDE"] = "FLAG_OUTSIDE"
    # Stateless by design: no identity continuity inferred across calls.
    history_retention: Literal[0] = 0
