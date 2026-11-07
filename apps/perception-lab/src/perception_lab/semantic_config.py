"""Explicit local semantic runtime configuration, independent of other perception."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SemanticConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)
    provider: Literal["synthetic", "pidnet", "pp_liteseg"] = "synthetic"
    weights: str | None = None
    sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")] | None = None
    width: Annotated[int, Field(ge=32, le=2048)] = 512
    height: Annotated[int, Field(ge=32, le=1024)] = 256
    threads: Annotated[int, Field(ge=1, le=8)] = 1
    device: Literal["cpu", "cuda:0"] = "cpu"
    max_age_ns: Annotated[int, Field(ge=1, le=5_000_000_000)] = 1_000_000_000
    # Explicit output profile, never guess whether a vendor tensor is labels or logits.
    output_kind: Literal["labels", "logits_nchw"] = "labels"
    pattern: Literal["sidewalk", "split", "path", "stairs", "unknown", "dynamic"] = "split"

    @model_validator(mode="after")
    def checkpoint(self) -> Self:
        if self.provider == "synthetic" and self.device != "cpu":
            raise ValueError("Synthetic semantics cannot claim GPU execution")
        if self.provider != "synthetic" and (self.weights is None or self.sha256 is None):
            raise ValueError("Real semantic provider requires a local hashed checkpoint")
        if self.provider == "synthetic" and (self.weights is not None or self.sha256 is not None):
            raise ValueError("Synthetic provider must not claim model weights")
        return self
