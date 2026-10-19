"""Research parameters; no production accuracy or probability calibration implied."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TrackerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)
    schema_version: Literal[1] = 1
    tracker_type: Literal["iou", "motion", "two_stage"] = "two_stage"
    motion_model: Literal["alpha_beta", "kalman"] = "alpha_beta"
    publication_threshold: Annotated[float, Field(ge=0, le=1)] = 0.25
    recovery_threshold: Annotated[float, Field(ge=0, le=1)] = 0.1
    minimum_hits: Annotated[int, Field(ge=2, le=20)] = 3
    confirmation_window_ns: Annotated[int, Field(gt=0, le=10_000_000_000)] = 1_000_000_000
    max_unobserved_ns: Annotated[int, Field(gt=0, le=10_000_000_000)] = 1_000_000_000
    max_step_ns: Annotated[int, Field(gt=0, le=30_000_000_000)] = 5_000_000_000
    max_tracks: Annotated[int, Field(ge=1, le=128)] = 64
    max_detections: Annotated[int, Field(ge=1, le=256)] = 128
    history_capacity: Annotated[int, Field(ge=1, le=128)] = 32
    min_iou: Annotated[float, Field(ge=0, le=1)] = 0.05
    center_gate: Annotated[float, Field(gt=0, le=10)] = 1.5
    center_weight: Annotated[float, Field(ge=0, le=1)] = 0.25
    class_penalty: Annotated[float, Field(ge=0, le=1)] = 0.2
    unmatched_cost: Annotated[float, Field(gt=0, le=3)] = 1.3
    duplicate_iou: Annotated[float, Field(gt=0.9, le=1)] = 0.98
    category_decay: Annotated[float, Field(gt=0, lt=1)] = 0.8
    alpha: Annotated[float, Field(gt=0, le=1)] = 0.8
    beta: Annotated[float, Field(gt=0, le=1)] = 0.2
    process_noise: Annotated[float, Field(gt=0, le=10000)] = 25.0
    measurement_noise: Annotated[float, Field(gt=0, le=10000)] = 4.0
    failure_quality_factor: Annotated[float, Field(gt=0, lt=1)] = 0.8

    @model_validator(mode="after")
    def thresholds(self) -> Self:
        if self.recovery_threshold > self.publication_threshold:
            raise ValueError("Recovery score must not exceed publication score")
        return self
