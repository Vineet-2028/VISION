"""CPU OpenCV boundary. One owner, bounded pair buffers, no model/network access."""

import importlib
from time import perf_counter_ns
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .config import canonical_hash
from .contracts import ComponentProvenance, FrameIdentity, PixelFormat
from .flow import DenseFlowField, FlowObservation, FramePair, SparseFlowObservation, restore_points
from .geometry import ImageMapping
from .motion_config import MotionConfig
from .preprocessing import PreparedImage


class ClassicalFlowProvider:
    def __init__(self, config: MotionConfig) -> None:
        self.c = config
        self.cv: Any = importlib.import_module("cv2")
        self.cv.setNumThreads(1)
        self.provenance = ComponentProvenance(
            config.flow_provider,
            "optical_flow",
            runtime="OpenCV-" + self.cv.__version__,
            configuration_hash=canonical_hash(config.model_dump()),
        )
        self.dis: Any = (
            self.cv.DISOpticalFlow_create(config.dis_preset)
            if config.flow_provider == "dis"
            else None
        )
        self.stage_ns: dict[str, int] = {}

    def estimate(
        self, a: NDArray[np.uint8], b: NDArray[np.uint8], pair: FramePair, mapping: ImageMapping
    ) -> FlowObservation:
        if a.shape != b.shape or a.ndim != 2 or a.dtype != np.uint8 or b.dtype != np.uint8:
            raise ValueError("Matching gray images required")
        if a.size > 1_048_576 or min(a.shape) < 16:
            raise ValueError("Flow resolution outside bounds")
        if (
            mapping.target_dimensions != (a.shape[1], a.shape[0])
            or mapping.camera_dimensions != (pair.width, pair.height)
            or mapping.camera_image_id != pair.camera_image_id
        ):
            raise ValueError("Flow mapping identity mismatch")
        start = perf_counter_ns()
        cv, c = self.cv, self.c
        if c.flow_provider == "dis":
            forward = np.asarray(self.dis.calc(a, b, None), dtype=np.float64)
            backward = np.asarray(self.dis.calc(b, a, None), dtype=np.float32)
            calculated = perf_counter_ns()
            y, x = np.mgrid[: a.shape[0], : a.shape[1]]
            bx, by = x + forward[:, :, 0], y + forward[:, :, 1]
            reverse = cv.remap(
                backward,
                bx.astype(np.float32),
                by.astype(np.float32),
                cv.INTER_LINEAR,
                borderMode=cv.BORDER_CONSTANT,
            )
            error = np.linalg.norm(forward + reverse, axis=2)
            valid = (
                (bx >= 0)
                & (by >= 0)
                & (bx < a.shape[1] - 1)
                & (by < a.shape[0] - 1)
                & np.isfinite(forward).all(axis=2)
                & np.isfinite(error)
                & (error <= c.fb_threshold)
            )
            forward = np.nan_to_num(forward, nan=0, posinf=0, neginf=0)
            error = np.nan_to_num(error, nan=1e9, posinf=1e9, neginf=1e9)
            self.stage_ns = {
                "features": 0,
                "flow": calculated - start,
                "filter": perf_counter_ns() - calculated,
            }
            return DenseFlowField(
                pair, forward, valid, error, mapping, self.provenance, start, perf_counter_ns()
            )
        points = cv.goodFeaturesToTrack(a, c.max_features, c.quality_level, c.min_distance)
        featured = perf_counter_ns()
        if points is None:
            self.stage_ns = {"features": featured - start, "flow": 0, "filter": 0}
            return SparseFlowObservation(
                pair,
                np.empty((0, 2)),
                np.empty((0, 2)),
                np.empty(0, dtype=np.bool_),
                np.empty(0),
                self.provenance,
                start,
                perf_counter_ns(),
            )
        options = dict(
            winSize=(c.window, c.window),
            maxLevel=c.pyramid_levels,
            criteria=(cv.TERM_CRITERIA_EPS | cv.TERM_CRITERIA_COUNT, 30, 0.01),
        )
        target, status, _ = cv.calcOpticalFlowPyrLK(a, b, points, None, **options)
        # Sanitize failed native coordinates before feeding them back to LK.
        finite = np.isfinite(target).all(axis=(1, 2))
        target = np.nan_to_num(target, nan=0, posinf=0, neginf=0)
        reverse, reverse_status, _ = cv.calcOpticalFlowPyrLK(b, a, target, None, **options)
        calculated = perf_counter_ns()
        error = np.linalg.norm(points.reshape(-1, 2) - reverse.reshape(-1, 2), axis=1)
        valid = (
            (status.ravel() != 0)
            & (reverse_status.ravel() != 0)
            & finite
            & np.isfinite(error)
            & (error <= c.fb_threshold)
        )
        target_xy = target.reshape(-1, 2)
        valid &= ((target_xy >= 0) & (target_xy < [a.shape[1] - 1, a.shape[0] - 1])).all(axis=1)
        error = np.nan_to_num(error, nan=1e9, posinf=1e9, neginf=1e9)
        # OpenCV integer pixel centers -> Sentinel continuous-edge centers.
        pa = restore_points(mapping, points.reshape(-1, 2).astype(np.float64) + 0.5)
        pb = restore_points(mapping, target.reshape(-1, 2).astype(np.float64) + 0.5)
        self.stage_ns = {
            "features": featured - start,
            "flow": calculated - featured,
            "filter": perf_counter_ns() - calculated,
        }
        return SparseFlowObservation(
            pair, pa, pb, valid, error, self.provenance, start, perf_counter_ns()
        )


class FlowAdapter:
    """One previous grayscale observation; identity gaps reset without fabricating flow."""

    def __init__(self, config: MotionConfig, session_id: str, calibration_hash: str) -> None:
        self.c, self.session_id, self.calibration_hash = config, session_id, calibration_hash
        self.provider = ClassicalFlowProvider(config)
        self.provenance = self.provider.provenance
        self.previous: tuple[FrameIdentity, NDArray[np.uint8], str] | None = None
        self.resets = 0

    def flow(self, image: PreparedImage, identity: FrameIdentity) -> FlowObservation | None:
        if image.descriptor.pixel_format != PixelFormat.RGB or image.descriptor.layout != "NHWC":
            raise ValueError("Flow requires RGB NHWC")
        cv = self.provider.cv
        h, w = image.pixels.shape[:2]
        factor = min(1.0, self.c.max_width / max(w, h))
        width, height = max(16, round(w * factor)), max(16, round(h * factor))
        gray = cv.cvtColor(image.pixels, cv.COLOR_RGB2GRAY)
        if (width, height) != (w, h):
            gray = cv.resize(gray, (width, height), interpolation=cv.INTER_AREA)
        mapping = image.mapping.scaled(width, height)
        previous = self.previous
        self.previous = (identity, gray, mapping.fingerprint)
        if previous is None:
            return None
        a, pixels, fingerprint = previous
        if (
            fingerprint != mapping.fingerprint
            or a.source_id != identity.source_id
            or a.timing != identity.timing
            or identity.sequence <= a.sequence
            or not 0 < identity.observation_ns - a.observation_ns <= self.c.max_gap_ns
        ):
            self.resets += 1
            return None
        pair = FramePair(
            self.session_id,
            a,
            identity,
            self.calibration_hash,
            mapping.camera_image_id,
            *mapping.camera_dimensions,
            self.c.max_gap_ns,
        )
        return self.provider.estimate(pixels, gray, pair, mapping)

    def close(self) -> None:
        self.previous = None
