"""Local tracking review schema. Draft links are never evaluation ground truth."""

from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .config import StrictModel
from .detection import P0_CLASSES, Box
from .detector_runtime import file_hash

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class TrackAnnotation(StrictModel):
    ground_truth_track_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
    label: str
    box: tuple[float, float, float, float]
    occlusion: Literal["VISIBLE", "PARTIAL", "HEAVY", "UNKNOWN"] = "UNKNOWN"

    @model_validator(mode="after")
    def valid(self) -> Self:
        if self.label not in P0_CLASSES or Box(*self.box).area <= 0:
            raise ValueError("Expected P0 category and positive box")
        return self


class TrackingFrame(StrictModel):
    image_id: str
    clip_id: str
    observation_ns: Annotated[int, Field(ge=0, le=2**63 - 1)]
    path: str
    sha256: Digest
    width: Annotated[int, Field(gt=0)]
    height: Annotated[int, Field(gt=0)]
    review_status: Literal["DRAFT_TRACK_LINK", "REVIEWED_TRACK_ID"] = "DRAFT_TRACK_LINK"
    annotations: tuple[TrackAnnotation, ...]
    motion: Literal["LOW", "MEDIUM", "HIGH", "UNKNOWN"] = "UNKNOWN"
    scene: Literal["CROWD", "TRAFFIC", "MIXED", "OTHER", "UNKNOWN"] = "UNKNOWN"

    @model_validator(mode="after")
    def valid(self) -> Self:
        ids = [a.ground_truth_track_id for a in self.annotations]
        if len(ids) != len(set(ids)):
            raise ValueError("Track ID duplicated within frame")
        for a in self.annotations:
            x1, y1, x2, y2 = a.box
            if not 0 <= x1 < x2 <= self.width or not 0 <= y1 < y2 <= self.height:
                raise ValueError("Reviewed box must be clipped to visible image")
        return self


class TrackingDataset(StrictModel):
    schema_version: Literal[1] = 1
    dataset: str
    source_sha256: Digest
    ownership: Literal["USER_OWNED_LOCAL_ONLY"] = "USER_OWNED_LOCAL_ONLY"
    sampling_fps: Annotated[int, Field(ge=5, le=10)] = 5
    purpose: Literal["TRACKING_DEVELOPMENT_REVIEW"] = "TRACKING_DEVELOPMENT_REVIEW"
    frames: tuple[TrackingFrame, ...]

    @model_validator(mode="after")
    def valid(self) -> Self:
        if not self.frames or len(self.frames) > 2500:
            raise ValueError("Review packet must contain 1..2500 frames")
        seen: set[str] = set()
        last: dict[str, int] = {}
        dimensions: dict[str, tuple[int, int]] = {}
        for f in self.frames:
            if f.image_id in seen or f.observation_ns <= last.get(f.clip_id, -1):
                raise ValueError("Duplicate identity or non-increasing clip timestamp")
            if dimensions.setdefault(f.clip_id, (f.width, f.height)) != (f.width, f.height):
                raise ValueError("Clip dimensions changed")
            last[f.clip_id] = f.observation_ns
            seen.add(f.image_id)
        return self


def validate_review(draft_path: Path, review_path: Path) -> TrackingDataset:
    draft = TrackingDataset.model_validate_json(draft_path.read_bytes())
    review = TrackingDataset.model_validate_json(review_path.read_bytes())
    if draft.model_dump(exclude={"frames"}) != review.model_dump(exclude={"frames"}):
        raise ValueError("Review changed dataset provenance")
    if len(draft.frames) != len(review.frames):
        raise ValueError("Review changed frame count")
    editable = {"annotations", "review_status", "motion", "scene"}
    for original, frame in zip(draft.frames, review.frames, strict=True):
        if original.model_dump(exclude=editable) != frame.model_dump(exclude=editable):
            raise ValueError("Review changed frozen frame identity")
        if frame.review_status != "REVIEWED_TRACK_ID":
            raise ValueError("HUMAN_TRACK_GROUND_TRUTH_REVIEW_REQUIRED")
        image = (draft_path.parent / frame.path).resolve()
        if (
            not image.is_relative_to(draft_path.parent.resolve())
            or file_hash(image) != frame.sha256
        ):
            raise ValueError("Review image provenance mismatch")
    return review
