"""Research interruption settings, not calibrated safety thresholds."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Duration = Annotated[int, Field(gt=0, le=300_000_000_000)]


class AttentionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    schema_version: Literal[1] = 1
    policy: Literal["NOVELTY_ESCALATION", "COOLDOWN", "NAIVE"] = "NOVELTY_ESCALATION"
    mode: Literal["BALANCED_ATTENTION", "CONSERVATIVE_ATTENTION"] = "BALANCED_ATTENTION"
    allow_degraded: bool = True
    cooldown_ns: Duration = 5_000_000_000
    repeat_interval_ns: Duration = 30_000_000_000
    global_interval_ns: Duration = 2_000_000_000
    rate_window_ns: Duration = 60_000_000_000
    max_interruptions: Annotated[int, Field(ge=1, le=60)] = 6
    event_validity_ns: Duration = 500_000_000
    reappearance_ns: Duration = 5_000_000_000
    history_retention_ns: Duration = 60_000_000_000
    max_entities: Annotated[int, Field(ge=1, le=512)] = 512
    escalation_override: bool = True
