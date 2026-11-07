"""Bounded research prediction settings; units are domain specific, not probabilities."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TrajectoryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)
    schema_version: Literal[1] = 1
    model: Literal["ADAPTIVE", "CONSTANT_POSITION", "CV_LAST_TWO", "CV_WINDOW"] = "ADAPTIVE"
    horizons_ns: tuple[int, ...] = (
        250_000_000,
        500_000_000,
        1_000_000_000,
        1_500_000_000,
        2_000_000_000,
        3_000_000_000,
    )
    history_count: Annotated[int, Field(ge=3, le=32)] = 16
    history_ns: Annotated[int, Field(ge=100_000_000, le=5_000_000_000)] = 2_000_000_000
    min_observations: Annotated[int, Field(ge=3, le=16)] = 3
    min_span_ns: Annotated[int, Field(ge=1, le=1_000_000_000)] = 100_000_000
    max_gap_ns: Annotated[int, Field(ge=1, le=3_000_000_000)] = 500_000_000
    max_age_ns: Annotated[int, Field(ge=1, le=3_000_000_000)] = 500_000_000
    pixel_floor: Annotated[float, Field(gt=0, le=100)] = 2.0
    bearing_floor: Annotated[float, Field(gt=0, le=1)] = 0.01
    world_floor: Annotated[float, Field(gt=0, le=10)] = 0.25
    outlier_multiplier: Annotated[float, Field(ge=2, le=10)] = 4.0
    growth_per_second: Annotated[float, Field(gt=0, le=10)] = 1.0
    long_horizon_ns: Annotated[int, Field(ge=1, le=3_000_000_000)] = 1_000_000_000

    @field_validator("horizons_ns", mode="before")
    @classmethod
    def json_horizons(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def bounds(self) -> Self:
        if not 1 <= len(self.horizons_ns) <= 8 or any(
            type(h) is not int or not 0 < h <= 3_000_000_000 for h in self.horizons_ns
        ):
            raise ValueError("One to eight positive horizons at most three seconds required")
        if tuple(sorted(set(self.horizons_ns))) != self.horizons_ns:
            raise ValueError("Horizons must be unique and increasing")
        if self.min_observations > self.history_count:
            raise ValueError("Minimum observations exceed history capacity")
        return self
