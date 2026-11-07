"""Versioned prototype policies, not calibrated safety thresholds."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WorldModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    schema_version: Literal[1] = 1
    max_entities: Annotated[int, Field(ge=1, le=512)] = 128
    history_count: Annotated[int, Field(ge=1, le=128)] = 16
    history_ns: Annotated[int, Field(ge=1, le=60_000_000_000)] = 5_000_000_000
    fresh_ns: Annotated[int, Field(ge=1, le=5_000_000_000)] = 500_000_000
    semantic_fresh_ns: Annotated[int, Field(ge=1, le=5_000_000_000)] = 1_000_000_000
    lost_ns: Annotated[int, Field(ge=1, le=30_000_000_000)] = 1_000_000_000
    expire_ns: Annotated[int, Field(ge=1, le=60_000_000_000)] = 3_000_000_000
    late_ns: Annotated[int, Field(ge=0, le=5_000_000_000)] = 1_000_000_000
    retention_ns: Annotated[int, Field(ge=1, le=60_000_000_000)] = 5_000_000_000
    diagnostic_count: Annotated[int, Field(ge=1, le=128)] = 32
    max_regions: Annotated[int, Field(ge=1, le=256)] = 128

    @model_validator(mode="after")
    def ordered(self) -> "WorldModelConfig":
        if self.fresh_ns > self.lost_ns or self.lost_ns >= self.expire_ns:
            raise ValueError("Require fresh <= lost < expiry")
        if max(self.fresh_ns, self.semantic_fresh_ns, self.late_ns) > self.retention_ns:
            raise ValueError("Retention must cover freshness and late window")
        return self
