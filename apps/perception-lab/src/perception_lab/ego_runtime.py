"""Bounded robust visual estimators. OpenCV values do not escape this boundary."""

import importlib
from time import perf_counter_ns
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .config import canonical_hash
from .contracts import ComponentProvenance
from .depth import DepthFrame
from .flow import SparseFlowObservation
from .geometry import CoreGeometry
from .motion import CameraMotionEstimate, MotionQuality, ScaleStatus
from .motion_config import MotionConfig
from .motion_geometry import depth_points, rays, require_calibration


def coverage(points: NDArray[np.float64], width: int, height: int) -> float:
    if not len(points):
        return 0.0
    cells = np.clip((points / np.array([width, height]) * 4).astype(int), 0, 3)
    return len(np.unique(cells[:, 0] + 4 * cells[:, 1])) / 16


def fit_rotation(a: NDArray[np.float64], b: NDArray[np.float64]) -> NDArray[np.float64]:
    u, _, vt = np.linalg.svd(b.T @ a)
    return np.asarray(u @ np.diag([1, 1, np.linalg.det(u @ vt)]) @ vt, dtype=np.float64)


class VisualEgoEstimator:
    def __init__(self, geometry: CoreGeometry, config: MotionConfig) -> None:
        self.g, self.c = geometry, config
        self.cv: Any = importlib.import_module("cv2")
        self.provenance = ComponentProvenance(
            "essential-and-rotation",
            "ego_motion",
            runtime="OpenCV-" + self.cv.__version__,
            configuration_hash=canonical_hash(config.model_dump()),
        )

    def estimate(
        self, flow: SparseFlowObservation, excluded: NDArray[np.bool_] | None = None
    ) -> CameraMotionEstimate:
        started = perf_counter_ns()
        require_calibration(self.g, flow.pair)
        c, cv = self.c, self.cv
        valid = flow.valid.copy()
        if excluded is not None:
            if excluded.shape != valid.shape or excluded.dtype != np.bool_:
                raise ValueError("Invalid exclusion mask")
            valid &= ~excluded
        a, b = rays(self.g, flow, "a"), rays(self.g, flow, "b")
        valid &= np.isfinite(a).all(axis=1) & np.isfinite(b).all(axis=1)
        count = int(valid.sum())
        cov = coverage(flow.points_a[valid], flow.pair.width, flow.pair.height)

        def result(
            reason: str,
            rotation: NDArray[np.float64] | None = None,
            direction: NDArray[np.float64] | None = None,
            inliers: int = 0,
            error: float | None = None,
            homography: float | None = None,
        ) -> CameraMotionEstimate:
            quality = MotionQuality(
                "DEGRADED" if rotation is not None else "UNAVAILABLE",
                reason,
                count,
                inliers,
                cov,
                inliers / count if count else 0,
                error,
                homography,
                self.g.c.calibration_quality.state,
            )
            return CameraMotionEstimate(
                flow.pair,
                rotation,
                direction,
                ScaleStatus.UP_TO_SCALE if direction is not None else ScaleStatus.NONE,
                quality,
                self.provenance,
                started,
                perf_counter_ns(),
            )

        if self.g.c.calibration_quality.state == "INVALID":
            return result("CALIBRATION_UNAVAILABLE")
        if count < c.minimum_features:
            return result(
                "DYNAMIC_SCENE_DOMINANT"
                if excluded is not None and excluded.mean() > 0.5
                else "INSUFFICIENT_FEATURES"
            )
        if cov < c.minimum_coverage:
            return result("POOR_SPATIAL_DISTRIBUTION")
        a, b = a[valid], b[valid]
        focal = min(self.g.c.intrinsics.fx, self.g.c.intrinsics.fy)
        threshold = c.ransac_pixels / focal
        rng = np.random.default_rng(c.seed)
        best = np.zeros(count, dtype=np.bool_)
        # Robust rotation-only candidate; outliers never get an ordinary least-squares vote.
        for _ in range(c.ransac_iterations):
            ids = rng.choice(count, 3, replace=False)
            rotation = fit_rotation(a[ids], b[ids])
            mask = np.linalg.norm(a @ rotation.T - b, axis=1) < threshold
            if mask.sum() > best.sum():
                best = mask
        if best.sum() >= c.minimum_features and best.mean() >= 0.85:
            if (
                coverage(flow.points_a[valid][best], flow.pair.width, flow.pair.height)
                < c.minimum_coverage
            ):
                return result("POOR_SPATIAL_DISTRIBUTION")
            rotation = fit_rotation(a[best], b[best])
            error = float(np.median(np.linalg.norm(a @ rotation.T - b, axis=1)[best]) * focal)
            return result(
                "PURE_ROTATION_LIKELY_OR_LOW_PARALLAX",
                rotation,
                inliers=int(best.sum()),
                error=error,
            )
        na, nb = a[:, :2] / a[:, 2:], b[:, :2] / b[:, 2:]
        # Undistorted normalized coordinates supplied by Guardian, never raw distorted pixels.
        cv.setRNGSeed(c.seed)
        homography, hm = cv.findHomography(
            na, nb, cv.RANSAC, threshold, maxIters=c.ransac_iterations, confidence=0.999
        )
        hs = float(np.count_nonzero(hm) / count) if hm is not None else 0.0
        if homography is not None and hs > 0.9:
            return result("PLANAR_DOMINANT", homography=hs)
        essential, mask = cv.findEssentialMat(
            na,
            nb,
            np.eye(3),
            method=cv.RANSAC,
            prob=0.999,
            threshold=threshold,
            maxIters=c.ransac_iterations,
        )
        if essential is None or essential.shape != (3, 3) or mask is None:
            return result("RANSAC_FAILURE", homography=hs)
        n, rotation, translation, inlier_mask = cv.recoverPose(
            essential, na, nb, np.eye(3), mask=mask
        )
        if n < c.minimum_features or n / count < c.minimum_inlier_ratio:
            return result("LOW_PARALLAX_OR_DYNAMIC_SCENE", homography=hs)
        selected = inlier_mask.ravel() != 0
        if (
            coverage(flow.points_a[valid][selected], flow.pair.width, flow.pair.height)
            < c.minimum_coverage
        ):
            return result("POOR_SPATIAL_DISTRIBUTION", homography=hs)
        return result(
            "VISUAL_UP_TO_SCALE_STATIC_MAJORITY_ASSUMED",
            np.asarray(rotation, dtype=np.float64),
            np.asarray(translation, dtype=np.float64).ravel(),
            int(n),
            homography=hs,
        )


class DepthAssistedEgoEstimator:
    """Explicit frame-A depth injection; no cache/latest-depth substitution."""

    def __init__(self, geometry: CoreGeometry, config: MotionConfig, depth: DepthFrame) -> None:
        self.g, self.c, self.depth = geometry, config, depth
        self.cv: Any = importlib.import_module("cv2")
        self.provenance = ComponentProvenance(
            "depth-pnp-research",
            "ego_motion",
            runtime="OpenCV-" + self.cv.__version__,
            configuration_hash=canonical_hash(config.model_dump()),
        )

    def estimate(
        self, flow: SparseFlowObservation, excluded: NDArray[np.bool_] | None = None
    ) -> CameraMotionEstimate:
        start = perf_counter_ns()
        xyz, rb = depth_points(self.g, flow, self.depth), rays(self.g, flow, "b")
        valid = flow.valid & np.isfinite(xyz).all(axis=1) & np.isfinite(rb).all(axis=1)
        if excluded is not None:
            if excluded.shape != valid.shape or excluded.dtype != np.bool_:
                raise ValueError("Invalid mask")
            valid &= ~excluded
        n = int(valid.sum())
        cov = coverage(flow.points_a[valid], flow.pair.width, flow.pair.height)
        reason, rotation, translation, inliers, error = "DEPTH_INSUFFICIENT", None, None, 0, None
        if n >= self.c.minimum_features and cov >= self.c.minimum_coverage:
            points = xyz[valid]
            # Reject near-collinear/planar geometry conservatively for this research baseline.
            singular = np.linalg.svd(points - points.mean(axis=0), compute_uv=False)
            if singular[-1] > singular[0] * 1e-3:
                normalized = rb[valid, :2] / rb[valid, 2:]
                self.cv.setRNGSeed(self.c.seed)
                ok, rv, tv, indices = self.cv.solvePnPRansac(
                    points,
                    normalized,
                    np.eye(3),
                    None,
                    iterationsCount=self.c.ransac_iterations,
                    reprojectionError=self.c.ransac_pixels
                    / min(self.g.c.intrinsics.fx, self.g.c.intrinsics.fy),
                    confidence=0.999,
                    flags=self.cv.SOLVEPNP_EPNP,
                )
                if (
                    ok
                    and indices is not None
                    and len(indices) >= self.c.minimum_features
                    and len(indices) / n >= self.c.minimum_inlier_ratio
                ):
                    rotation = np.asarray(self.cv.Rodrigues(rv)[0], dtype=np.float64)
                    translation = np.asarray(tv, dtype=np.float64).ravel()
                    inliers = len(indices)
                    predicted = points @ rotation.T + translation
                    error = float(
                        np.median(
                            np.linalg.norm(
                                predicted[:, :2] / predicted[:, 2:] - normalized, axis=1
                            )[indices.ravel()]
                        )
                    )
                    reason = "UNVALIDATED_SCALE"
                else:
                    reason = "RANSAC_FAILURE"
            else:
                reason = "DEGENERATE_DEPTH_GEOMETRY"
        quality = MotionQuality(
            "DEGRADED" if rotation is not None else "UNAVAILABLE",
            reason,
            n,
            inliers,
            cov,
            inliers / n if n else 0,
            error,
            calibration_quality=self.g.c.calibration_quality.state,
        )
        return CameraMotionEstimate(
            flow.pair,
            rotation,
            None,
            ScaleStatus.DEPTH_SCALED_RESEARCH if rotation is not None else ScaleStatus.NONE,
            quality,
            self.provenance,
            start,
            perf_counter_ns(),
            translation,
            self.depth.provenance if rotation is not None else None,
        )
