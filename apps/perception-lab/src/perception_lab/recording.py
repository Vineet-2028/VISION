"""Opt-in JSONL, bounded debug images, and exclusive session artifact creation."""

import json
import os
import platform
import time
from dataclasses import asdict, fields
from importlib.metadata import version
from pathlib import Path
from typing import Any, TextIO
from uuid import uuid4

from . import __version__
from .config import Calibration, LabConfig, canonical_hash
from .contracts import Event, Frame, FrameResult, LabError, PixelFormat
from .motion import CameraMotionEstimate


class SessionRecorder:
    def __init__(self, config: LabConfig, calibration: Calibration, output: Path) -> None:
        self.session_id = str(uuid4())
        self.config = config
        self.closed = False
        self.debug_saved = 0
        self.directory: Path | None = None
        self.stream: TextIO | None = None
        public = config.public_configuration()
        calibration_public = calibration.model_dump(exclude={"metadata"})
        self.manifest: dict[str, Any] = {
            "schema_version": 4
            if config.motion is not None
            else 3
            if config.depth is not None
            else (2 if config.tracker is not None else 1),
            "session_id": self.session_id,
            "source_id": config.source_id,
            "source_type": config.source_type,
            "configuration": public,
            "configuration_hash": canonical_hash(public),
            "calibration": calibration_public,
            "calibration_hash": canonical_hash(calibration_public),
            "software_version": __version__,
            "processing_clock": {
                "name": "perf_counter_ns",
                "monotonic": time.get_clock_info("perf_counter").monotonic,
                "resolution_seconds": time.get_clock_info("perf_counter").resolution,
            },
            "git_revision": None,
            "machine": {
                "os": platform.system(),
                "logical_cpu_count": os.cpu_count(),
                "python": platform.python_version(),
                "libraries": {
                    name: version(name) for name in ("av", "numpy", "JPype1", "pydantic")
                },
            },
            "termination_reason": "RUNNING",
        }
        if config.record_session:
            output.mkdir(parents=True, exist_ok=True)
            self.directory = output.resolve() / self.session_id
            self.directory.mkdir(exist_ok=False)
            self.stream = (self.directory / "frames.jsonl").open("x", encoding="utf-8")
            try:
                self._write_manifest()
            except BaseException:
                self.stream.close()
                raise

    def _write_manifest(self) -> None:
        if self.directory is not None:
            temporary = self.directory / "manifest.tmp"
            with temporary.open("w", encoding="utf-8") as stream:
                json.dump(self.manifest, stream, sort_keys=True, allow_nan=False, indent=2)
                stream.flush()
            temporary.replace(self.directory / "manifest.json")

    def write_event(self, event: Event) -> None:
        if self.stream is not None:
            self._write({"schema_version": 1, "type": "event", **asdict(event)})

    def write_result(self, result: FrameResult) -> None:
        if self.stream is not None:
            if result.optical_flow is not None:
                self.manifest["schema_version"] = 4
            elif result.depth is not None:
                # Injected adapters are also supported; final manifest must match
                # the depth-capable records even without config.depth.
                self.manifest["schema_version"] = max(3, self.manifest["schema_version"])
            self._write(
                {
                    "schema_version": 4
                    if result.optical_flow is not None
                    else 3
                    if result.depth is not None
                    else (2 if result.tracks is not None else 1),
                    "type": "frame_result",
                    **{
                        f.name: asdict(getattr(result, f.name))
                        if hasattr(getattr(result, f.name), "__dataclass_fields__")
                        else getattr(result, f.name)
                        for f in fields(result)
                        if f.name
                        not in {
                            "depth",
                            "components",
                            "detection_depths",
                            "track_depths",
                            "optical_flow",
                            "camera_motion",
                            "track_image_motion",
                        }
                    },
                    "components": [asdict(c) for c in result.components],
                    "detection_depths": [
                        asdict(d) if d is not None else None for d in result.detection_depths
                    ],
                    "track_depths": [asdict(d) for d in result.track_depths],
                    "depth": result.depth.summary() if result.depth is not None else None,
                    "optical_flow": result.optical_flow.summary()
                    if result.optical_flow is not None
                    else None,
                    "camera_motion": motion_summary(result.camera_motion),
                    "track_image_motion": [asdict(m) for m in result.track_image_motion],
                }
            )

    def _write(self, record: dict[str, Any]) -> None:
        if self.closed:
            raise LabError("RECORDER_CLOSED")
        if self.stream is not None:
            self.stream.write(
                json.dumps(record, sort_keys=True, allow_nan=False, separators=(",", ":")) + "\n"
            )

    def debug_frame(self, frame: Frame) -> None:
        every = self.config.debug_every_n
        if (
            self.directory is None
            or every is None
            or frame.identity.sequence % every
            or self.debug_saved >= self.config.debug_max_frames
        ):
            return
        if frame.pixel_format != PixelFormat.RGB:
            raise LabError("DEBUG_REQUIRES_RGB")
        with (self.directory / f"debug-{frame.identity.sequence}.ppm").open("xb") as stream:
            stream.write(f"P6\n{frame.width} {frame.height}\n255\n".encode("ascii"))
            stream.write(frame.pixels.tobytes())
        self.debug_saved += 1

    def finish(self, summary: dict[str, Any], reason: str, failure: str | None = None) -> None:
        self.manifest.update(summary=summary, termination_reason=reason, failure=failure)
        try:
            self.close()
            if self.directory is not None:
                with (self.directory / "metrics.json").open("x", encoding="utf-8") as stream:
                    json.dump(
                        {"schema_version": 1, **summary}, stream, sort_keys=True, allow_nan=False
                    )
        except BaseException:
            self.manifest.update(termination_reason="FATAL", failure="RECORDER_FINALIZATION_FAILED")
            self._write_manifest()
            raise
        self._write_manifest()

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            if self.stream is not None:
                self.stream.close()


def motion_summary(motion: "CameraMotionEstimate | None") -> dict[str, Any] | None:
    if motion is None:
        return None
    return {
        "pair": asdict(motion.pair),
        "rotation": motion.rotation.tolist() if motion.rotation is not None else None,
        "translation_direction": motion.translation_direction.tolist()
        if motion.translation_direction is not None
        else None,
        "research_translation": motion.research_translation.tolist()
        if motion.research_translation is not None
        else None,
        "scale_status": motion.scale_status,
        "quality": asdict(motion.quality),
        "provenance": asdict(motion.provenance),
        "scale_source": asdict(motion.scale_source) if motion.scale_source else None,
        "started_ns": motion.started_ns,
        "completed_ns": motion.completed_ns,
    }
