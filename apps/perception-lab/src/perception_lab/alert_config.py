"""Versioned prototype presentation limits, not human reaction-time thresholds."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class AlertConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    schema_version: Literal[1] = 1
    template_version: Literal["english-v1"] = "english-v1"
    category_mapping: Literal["conservative-v1"] = "conservative-v1"
    direction_mapping: Literal["cardinal-v1"] = "cardinal-v1"
    repeat_style: Literal["FULL_PHRASE"] = "FULL_PHRASE"
    escalation_style: Literal["EMPHASIS_METADATA"] = "EMPHASIS_METADATA"
    max_words: Annotated[int, Field(ge=1, le=12)] = 6
    max_characters: Annotated[int, Field(ge=8, le=120)] = 64
    words_per_minute: Annotated[int, Field(ge=80, le=300)] = 180
    max_age_ns: Annotated[int, Field(gt=0, le=500_000_000)] = 500_000_000
    late_after_ns: Annotated[int, Field(ge=0, le=500_000_000)] = 200_000_000
    sink_mode: Literal["RECORDING", "NULL"] = "RECORDING"
    queue_size: Literal[1] = 1
    history_size: Annotated[int, Field(ge=1, le=512)] = 128
