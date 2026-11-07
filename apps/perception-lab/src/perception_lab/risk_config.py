"""Versioned prototype ranking policy; no calibrated safety thresholds."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class RiskConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)
    schema_version: Literal[1] = 1
    engine: Literal["rule_based"] = "rule_based"
    max_source_age_ns: Annotated[int, Field(gt=0, le=3_000_000_000)] = 500_000_000
    urgent_entry_ns: Annotated[int, Field(gt=0, le=3_000_000_000)] = 1_000_000_000
    validity_ns: Annotated[int, Field(gt=0, le=1_000_000_000)] = 500_000_000
    history_retention_ns: Annotated[int, Field(gt=0, le=3_000_000_000)] = 1_000_000_000
    max_entities: Annotated[int, Field(gt=0, le=512)] = 512
    max_hypotheses: Annotated[int, Field(gt=0, le=2048)] = 2048
    unvalidated_ttc_policy: Literal["DIAGNOSTIC_ONLY"] = "DIAGNOSTIC_ONLY"
    physical_evidence_policy: Literal["NO_PHYSICAL_AUTHORITY"] = "NO_PHYSICAL_AUTHORITY"
