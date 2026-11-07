"""Strict, finite, versioned configuration and calibration serialization boundaries."""

import hashlib
import json
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .alert_config import AlertConfig
from .attention_config import AttentionConfig
from .corridor_config import CorridorConfig
from .depth_config import DepthConfig
from .interaction_config import InteractionConfig
from .motion_config import MotionConfig
from .risk_config import RiskConfig
from .semantic_config import SemanticConfig
from .tracking_config import TrackerConfig
from .trajectory_config import TrajectoryConfig
from .world_config import WorldModelConfig

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")]
PositiveInt = Annotated[int, Field(gt=0, le=2**31 - 1)]
Nanoseconds = Annotated[int, Field(ge=0, le=2**63 - 1)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)


def read_json(path: Path, *, max_bytes: int = 1_000_000) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    if path.stat().st_size > max_bytes:
        raise ValueError("Configuration exceeds size limit")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)


def canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


class Resolution(StrictModel):
    width: PositiveInt
    height: PositiveInt


class Intrinsics(StrictModel):
    fx: Annotated[float, Field(gt=0)]
    fy: Annotated[float, Field(gt=0)]
    cx: float
    cy: float
    skew: Literal[0]


class Extrinsics(StrictModel):
    version: Identifier
    device_frame_id: Identifier
    rotation_wxyz: Annotated[list[float], Field(min_length=4, max_length=4)]
    translation_meters: Annotated[list[float], Field(min_length=3, max_length=3)]


class Quality(StrictModel):
    state: Literal["UNKNOWN", "VALID", "DEGRADED", "INVALID"]
    rms_pixels: Annotated[float, Field(ge=0)] | None
    sample_count: PositiveInt | None
    timestamp_epoch_millis: Nanoseconds | None

    @model_validator(mode="after")
    def evidence(self) -> Self:
        if self.state == "VALID" and (self.rms_pixels is None or self.sample_count is None):
            raise ValueError("VALID requires fit evidence")
        return self


class Calibration(StrictModel):
    schema_version: Literal[1]
    camera_id: Identifier
    calibration_version: Identifier
    camera_frame_id: Identifier
    image_frame_id: Identifier
    pixel_convention: Literal["continuous_edges"]
    resolution: Resolution
    intrinsics: Intrinsics
    distortion_model: Literal["none", "brown_conrady"]
    distortion_coefficients: dict[str, float]
    camera_to_device: Extrinsics | None = None
    calibration_quality: Quality
    metadata: str | None = None

    @model_validator(mode="after")
    def coefficients(self) -> Self:
        required = {"k1", "k2", "k3", "p1", "p2", "max_radius"}
        if set(self.distortion_coefficients) != (
            required if self.distortion_model == "brown_conrady" else set()
        ):
            raise ValueError("Wrong distortion coefficients")
        return self


class PreprocessConfig(StrictModel):
    operation: Literal["identity", "resize", "crop", "letterbox"] = "identity"
    width: PositiveInt | None = None
    height: PositiveInt | None = None
    left: Annotated[int, Field(ge=0)] = 0
    top: Annotated[int, Field(ge=0)] = 0
    pixel_format: Literal["RGB", "BGR", "GRAY", "RGBA"] = "RGB"
    layout: Literal["NHWC", "NCHW"] = "NHWC"

    @model_validator(mode="after")
    def dimensions(self) -> Self:
        if self.operation != "identity" and (self.width is None or self.height is None):
            raise ValueError("Geometry operation requires dimensions")
        if self.operation == "identity" and (self.width is not None or self.height is not None):
            raise ValueError("Identity must not change dimensions")
        return self


class DetectorConfig(StrictModel):
    runtime: Literal["ultralytics", "rtdetr", "yolox", "picodet"] = "ultralytics"
    weights: str
    sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    input_size: Literal[416, 512, 640, 768] = 640
    confidence: Annotated[float, Field(ge=0, le=1)] = 0.05
    device: Literal["cpu", "cuda:0"] = "cpu"
    half: bool = False
    threads: Annotated[int, Field(ge=1, le=16)] = 1


class LabConfig(StrictModel):
    schema_version: Literal[1] = 1
    realtime_rescue: bool = False
    camera_view_health: bool = False
    orientation_canonicalization: bool = False
    entity_semantics_ontology: str | None = None
    semantic_presentation_enabled: bool = True
    mode: Literal["OFFLINE_REPLAY", "REALTIME"] = "OFFLINE_REPLAY"
    source_type: Literal["VIDEO_FILE"] = "VIDEO_FILE"
    source_id: Identifier = "local-video"
    input: str
    calibration: str
    queue_capacity: Annotated[int, Field(ge=1, le=64)] = 2
    drop_policy: Literal["PROCESS_ALL", "DROP_OLDEST", "LATEST_FRAME"] = "PROCESS_ALL"
    max_staleness_ns: Nanoseconds | None = None
    intervals_ns: dict[Literal["detector", "depth", "segmentation", "optical_flow"], PositiveInt]
    preprocess: PreprocessConfig = PreprocessConfig()
    detector: DetectorConfig | None = None
    tracker: TrackerConfig | None = None
    depth: DepthConfig | None = None
    motion: MotionConfig | None = None
    segmentation: SemanticConfig | None = None
    world_model: WorldModelConfig | None = None
    corridor: CorridorConfig | None = None
    trajectory: TrajectoryConfig | None = None
    interaction: InteractionConfig | None = None
    risk: RiskConfig | None = None
    attention: AttentionConfig | None = None
    alerts: AlertConfig | None = None
    visualization: bool = False
    source_scaling: Resolution | None = None
    record_session: bool = False
    output: str = "benchmark-results"
    debug_every_n: PositiveInt | None = None
    debug_max_frames: Annotated[int, Field(ge=0, le=100)] = 0
    start_ns: Nanoseconds = 0
    end_ns: Nanoseconds | None = None
    metrics_window: Annotated[int, Field(ge=1, le=10000)] = 2048
    max_pixels: Annotated[int, Field(ge=1, le=33_177_600)] = 8_294_400

    @model_validator(mode="after")
    def consistency(self) -> Self:
        if self.orientation_canonicalization and (
            self.preprocess.operation != "identity" or self.preprocess.layout != "NHWC"
        ):
            raise ValueError("Orientation canonicalization requires identity NHWC preprocessing")
        if self.realtime_rescue and (
            self.mode != "REALTIME"
            or self.queue_capacity != 1
            or self.drop_policy != "LATEST_FRAME"
        ):
            raise ValueError("Realtime rescue requires REALTIME and a single latest-frame slot")
        if self.realtime_rescue and (self.visualization or self.record_session):
            raise ValueError("Realtime rescue excludes blocking debug rendering/recording")
        if self.alerts is not None and self.attention is None:
            raise ValueError("Alerts require explicit attention configuration")
        if self.attention is not None and self.risk is None:
            raise ValueError("Attention requires explicit risk configuration")
        if self.risk is not None and self.world_model is None:
            raise ValueError(
                "Risk requires world state; absent spatial evidence remains undetermined"
            )
        if self.interaction is not None and (self.trajectory is None or self.corridor is None):
            raise ValueError("Interaction requires trajectory and corridor analysis")
        if self.trajectory is not None and self.world_model is None:
            raise ValueError("Trajectory prediction requires WorldState")
        if self.corridor is not None and self.world_model is None:
            raise ValueError("Corridor analysis requires WorldState")
        if self.segmentation is not None:
            if "segmentation" not in self.intervals_ns:
                raise ValueError("Segmentation requires scheduler interval")
            if self.preprocess.pixel_format != "RGB" or self.preprocess.layout != "NHWC":
                raise ValueError("Segmentation requires RGB NHWC")
        if self.motion is not None:
            if "optical_flow" not in self.intervals_ns:
                raise ValueError("Motion requires optical_flow scheduler interval")
            if self.preprocess.pixel_format != "RGB" or self.preprocess.layout != "NHWC":
                raise ValueError("Motion requires RGB NHWC")
        if self.depth is not None:
            if "depth" not in self.intervals_ns:
                raise ValueError("Configured depth requires scheduler interval")
            if self.preprocess.pixel_format != "RGB" or self.preprocess.layout != "NHWC":
                raise ValueError("Depth requires RGB NHWC")
        if self.tracker is not None:
            if self.detector is None:
                raise ValueError("Tracking requires an explicitly configured detector")
            if self.detector.confidence > self.tracker.recovery_threshold:
                raise ValueError(
                    "Detector score floor hides configured tracking recovery proposals"
                )
        if self.mode == "OFFLINE_REPLAY" and self.drop_policy != "PROCESS_ALL":
            raise ValueError("Offline replay preserves every valid frame")
        if self.mode == "REALTIME" and (
            self.drop_policy == "PROCESS_ALL" or self.max_staleness_ns is None
        ):
            raise ValueError("Realtime requires explicit drop policy and freshness limit")
        if self.end_ns is not None and self.end_ns <= self.start_ns:
            raise ValueError("End must follow start")
        if bool(self.debug_every_n) != bool(self.debug_max_frames):
            raise ValueError("Debug images require both sampling and a finite cap")
        if self.debug_every_n and not self.record_session:
            raise ValueError("Debug images require explicit recording")
        if not self.intervals_ns:
            raise ValueError("Configure at least one component interval")
        if self.detector is not None:
            if "detector" not in self.intervals_ns:
                raise ValueError("Configured detector requires a scheduler interval")
            if self.preprocess.pixel_format != "RGB" or self.preprocess.layout != "NHWC":
                raise ValueError("Detector requires RGB NHWC")
            if self.detector.half and self.detector.device == "cpu":
                raise ValueError("FP16 requires a supported GPU")
        if self.preprocess.width is not None and self.preprocess.height is not None:
            if self.preprocess.width * self.preprocess.height > self.max_pixels:
                raise ValueError("Preprocessed image exceeds pixel limit")
        if self.source_scaling is not None:
            if self.source_scaling.width * self.source_scaling.height > self.max_pixels:
                raise ValueError("Source scaling exceeds pixel limit")
        return self

    def public_configuration(self) -> dict[str, Any]:
        # Paths are operational input, never portable session metadata.
        result = self.model_dump(exclude={"input", "calibration", "output"})
        if result["detector"] is not None:
            result["detector"].pop("weights")
        if result["depth"] is not None:
            result["depth"].pop("weights")
        if result["segmentation"] is not None:
            result["segmentation"].pop("weights")
        return result
