"""Validated local evaluation manifests. Original-camera continuous edges only."""

from collections import Counter
from pathlib import Path
from typing import Annotated, Any, Literal, Self

import av
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .detection import P0_CLASSES, Box, ObjectClass
from .detector_runtime import file_hash

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Scenario(StrictModel):
    lighting: Literal["DAY", "DUSK", "NIGHT", "LOW_LIGHT", "UNKNOWN"]
    motion: Literal["LOW", "MEDIUM", "HIGH", "UNKNOWN"]
    occlusion: Literal["NONE", "PARTIAL", "HEAVY", "UNKNOWN"]
    environment: Literal[
        "CAMPUS", "SIDEWALK", "ROAD_EDGE", "CROSSWALK", "CROWD", "OTHER", "UNKNOWN"
    ]
    blur: Literal["PRESENT", "ABSENT", "UNKNOWN"]
    provenance: Literal["HUMAN_REVIEWED", "SOURCE_ANNOTATION", "DERIVED", "UNKNOWN"]


class Annotation(StrictModel):
    label: str
    box: tuple[float, float, float, float]
    ignore: bool = False
    crowd: bool = False
    truncated: bool | None = None
    occluded: bool | None = None
    occlusion_state: Literal["UNKNOWN", "VISIBLE", "PARTIALLY_OCCLUDED", "HEAVILY_OCCLUDED"] = (
        "UNKNOWN"
    )
    difficulty: str = "UNKNOWN"

    @model_validator(mode="after")
    def check(self) -> Self:
        if self.label not in {*P0_CLASSES, "SHELTER"} or Box(*self.box).area <= 0:
            raise ValueError("Expected supported annotation class and positive-area box")
        if self.occluded is not None and self.occlusion_state != "UNKNOWN":
            if self.occluded != (self.occlusion_state != "VISIBLE"):
                raise ValueError("Conflicting occlusion labels")
        return self


class EvaluationFrame(StrictModel):
    image_id: str = Field(min_length=1)
    sequence_id: str = Field(min_length=1)
    split: Literal["TRAIN_DEV", "CALIBRATION", "TEST"]
    observation_ns: int = Field(ge=0)
    path: str
    sha256: Digest
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    coordinate_space: Literal["ORIGINAL_CAMERA_CONTINUOUS_EDGES"]
    annotations_reviewed: bool
    metadata: Scenario
    annotations: tuple[Annotation, ...]

    @model_validator(mode="after")
    def check(self) -> Self:
        seen = set()
        for annotation in self.annotations:
            x1, y1, x2, y2 = annotation.box
            if (
                x1 < 0 or y1 < 0 or x2 > self.width or y2 > self.height
            ) and not annotation.truncated:
                raise ValueError("Out-of-image box requires explicit truncation")
            if x2 <= 0 or y2 <= 0 or x1 >= self.width or y1 >= self.height:
                raise ValueError("Box has no image intersection")
            key = (annotation.label, annotation.box)
            if key in seen:
                raise ValueError("Duplicate annotation")
            seen.add(key)
        return self


class Sequence(StrictModel):
    sequence_id: str
    media_sha256: Digest
    source_url_or_reference: str = Field(min_length=1)
    license_reference: str = Field(min_length=1)
    permission_status: Literal["REVIEW_REQUIRED", "APPROVED_FOR_LOCAL_EVALUATION"]
    sampling_fps: float = Field(gt=0, le=30)
    sampling_policy: str = Field(min_length=1)
    parent_video_id: str | None = None
    start_ns: int | None = Field(default=None, ge=0)
    end_ns: int | None = Field(default=None, gt=0)


class EvaluationDataset(StrictModel):
    schema_version: Literal[1, 2, 3]
    dataset: str = Field(min_length=1)
    scope: Literal["SENTINEL_REAL_WORLD"]
    annotation_sha256: Digest
    sequences: tuple[Sequence, ...]
    images: tuple[EvaluationFrame, ...]

    @model_validator(mode="after")
    def check(self) -> Self:
        if not self.images or not self.sequences:
            raise ValueError("An empty plan is not an evaluation dataset")
        ids = [s.sequence_id for s in self.sequences]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate sequence")
        if self.schema_version == 1 and len({s.media_sha256 for s in self.sequences}) != len(ids):
            raise ValueError("Duplicate source media")
        seen_ids, seen_hashes, seen_times = set(), set(), set()
        splits: dict[str, str] = {}
        for frame in self.images:
            if self.schema_version < 3 and any(a.label == "SHELTER" for a in frame.annotations):
                raise ValueError("Context annotations require dataset schema version 3")
            if frame.sequence_id not in ids:
                raise ValueError("Unknown source sequence")
            if frame.image_id in seen_ids or frame.sha256 in seen_hashes:
                raise ValueError("Duplicate frame ID or identical image content")
            key = (frame.sequence_id, frame.observation_ns)
            if key in seen_times:
                raise ValueError("Duplicate sampled observation")
            if splits.setdefault(frame.sequence_id, frame.split) != frame.split:
                raise ValueError("Sequence leakage between calibration and test")
            seen_ids.add(frame.image_id)
            seen_hashes.add(frame.sha256)
            seen_times.add(key)
        if self.schema_version >= 2:
            for sequence in self.sequences:
                if (
                    sequence.parent_video_id != sequence.media_sha256
                    or sequence.start_ns is None
                    or sequence.end_ns is None
                    or sequence.end_ns <= sequence.start_ns
                ):
                    raise ValueError(
                        "Version 2 requires hash-bound parent and positive temporal window"
                    )
                if sequence.sequence_id not in splits:
                    raise ValueError("Empty sequence")
                for frame in self.images:
                    if (
                        frame.sequence_id == sequence.sequence_id
                        and not sequence.start_ns <= frame.observation_ns < sequence.end_ns
                    ):
                        raise ValueError("Frame outside sequence window")
            for i, a in enumerate(self.sequences):
                for b in self.sequences[i + 1 :]:
                    if a.media_sha256 != b.media_sha256:
                        continue
                    assert a.start_ns is not None and a.end_ns is not None
                    assert b.start_ns is not None and b.end_ns is not None
                    gap = max(a.start_ns, b.start_ns) - min(a.end_ns, b.end_ns)
                    if gap < 0 or (
                        splits[a.sequence_id] != splits[b.sequence_id] and gap < 60_000_000_000
                    ):
                        raise ValueError(
                            "Overlapping windows or cross-split guard band below 60 seconds"
                        )
        return self


def audit_dataset(path: Path, annotations: Path) -> dict[str, Any]:
    dataset = EvaluationDataset.model_validate_json(path.read_bytes())
    if file_hash(annotations) != dataset.annotation_sha256:
        raise ValueError("Annotation provenance hash mismatch")
    classes: Counter[str] = Counter()
    context_classes: Counter[str] = Counter()
    scenarios: dict[str, Counter[str]] = {key: Counter() for key in Scenario.model_fields}
    for frame in dataset.images:
        image_path = (path.parent / frame.path).resolve()
        if not image_path.is_relative_to(path.parent.resolve()):
            raise ValueError("Image escapes dataset directory")
        if file_hash(image_path) != frame.sha256:
            raise ValueError("Frame hash mismatch")
        with av.open(
            str(image_path),
            options={
                "format_whitelist": (
                    "image2,image2pipe,jpeg_pipe,png_pipe,ppm_pipe,bmp_pipe,webp_pipe"
                ),
                "protocol_whitelist": "file",
            },
        ) as container:
            decoded = next(container.decode(video=0))
            if (decoded.width, decoded.height) != (frame.width, frame.height):
                raise ValueError("Decoded frame dimension mismatch")
        if not frame.annotations_reviewed:
            raise ValueError("Unreviewed annotations cannot be treated as ground truth")
        for item in frame.annotations:
            if not item.ignore and not item.crowd:
                if item.label in P0_CLASSES:
                    classes[ObjectClass(item.label).value] += 1
                else:
                    context_classes[item.label] += 1
        for key, value in frame.metadata.model_dump().items():
            scenarios[key][value] += 1
    if any(s.permission_status != "APPROVED_FOR_LOCAL_EVALUATION" for s in dataset.sequences):
        raise ValueError("Source permission review incomplete")
    return {
        "dataset": dataset.dataset,
        "manifest_sha256": file_hash(path),
        "frames": len(dataset.images),
        "sequences": len(dataset.sequences),
        "objects": sum(classes.values()),
        "classes": dict(classes),
        "context_classes_excluded_from_p0": dict(context_classes),
        "scenarios": {key: dict(value) for key, value in scenarios.items()},
        "quality_limit": "Structural checks do not prove semantic annotation accuracy",
    }


def sample_indices(observations_ns: list[int], fps: float) -> tuple[int, ...]:
    """First actual PTS on/after each grid deadline; never duplicate a decoded frame."""
    if not 0 < fps <= 30 or any(
        b <= a for a, b in zip(observations_ns, observations_ns[1:], strict=False)
    ):
        raise ValueError("Expected finite positive FPS and strictly increasing PTS")
    if not observations_ns:
        return ()
    if observations_ns[0] < 0:
        raise ValueError("Negative observation")
    period = round(1e9 / fps)
    anchor = observations_ns[0]
    due = anchor
    selected = []
    for index, observation in enumerate(observations_ns):
        if observation >= due:
            selected.append(index)
            due = anchor + ((observation - anchor) // period + 1) * period
    return tuple(selected)
