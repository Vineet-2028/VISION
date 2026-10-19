"""Explicit optional depth configuration; models are loaded once per replay."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DepthConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)
    provider: Literal["synthetic", "dav2_relative", "dav2_metric_outdoor"]
    weights: str | None = None
    sha256: Annotated[str, Field(pattern="^[a-f0-9]{64}$")] | None = None
    config_sha256: Annotated[str, Field(pattern="^[a-f0-9]{64}$")] | None = None
    processor_sha256: Annotated[str, Field(pattern="^[a-f0-9]{64}$")] | None = None
    input_size: Literal[266, 392, 518] = 266
    threads: Annotated[int, Field(ge=1, le=16)] = 1
    synthetic_meters: Annotated[float, Field(gt=0, le=100)] = 5.0

    @model_validator(mode="after")
    def artifact(self) -> Self:
        if self.provider != "synthetic" and not all(
            (self.weights, self.sha256, self.config_sha256, self.processor_sha256)
        ):
            raise ValueError("Real depth requires local weights and artifact hashes")
        return self
