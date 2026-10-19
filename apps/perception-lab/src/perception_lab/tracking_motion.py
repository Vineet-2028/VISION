"""Dedicated four independent position/velocity filters; pixels, never meters."""

import numpy as np
from numpy.typing import NDArray

from .detection import Box
from .tracking_config import TrackerConfig


def measurement(box: Box) -> NDArray[np.float64]:
    return np.array(
        [(box.x1 + box.x2) / 2, (box.y1 + box.y2) / 2, box.x2 - box.x1, box.y2 - box.y1],
        dtype=np.float64,
    )


class ImageMotion:
    def __init__(self, box: Box, config: TrackerConfig) -> None:
        self.config = config
        self.position = measurement(box)
        self.velocity = np.zeros(4, dtype=np.float64)
        self.covariance = np.tile(np.diag([config.measurement_noise, 100.0]), (4, 1, 1))

    def predict(self, dt: float) -> Box:
        if self.config.tracker_type != "iou":
            self.position = self.position + dt * self.velocity
        transition = np.array([[1.0, dt], [0.0, 1.0]])
        noise = self.config.process_noise * np.array([[dt**4 / 4, dt**3 / 2], [dt**3 / 2, dt**2]])
        self.covariance = transition @ self.covariance @ transition.T + noise
        return self.box()

    def correct(self, box: Box, observation_dt: float, previous: Box) -> None:
        z = measurement(box)
        if self.config.tracker_type == "iou":
            self.position = z
        elif self.config.motion_model == "alpha_beta":
            # Velocity uses observation-to-observation dt, not last prediction-tick dt.
            self.velocity = (1 - self.config.beta) * self.velocity + self.config.beta * (
                z - measurement(previous)
            ) / observation_dt
            self.position = (1 - self.config.alpha) * self.position + self.config.alpha * z
            self.covariance[:, 0, :] = 0
            self.covariance[:, :, 0] = 0
            self.covariance[:, 0, 0] = self.config.measurement_noise
        else:
            gain = (
                self.covariance[:, :, 0]
                / (self.covariance[:, 0, 0] + self.config.measurement_noise)[:, None]
            )
            residual = z - self.position
            self.position += gain[:, 0] * residual
            self.velocity += gain[:, 1] * residual
            # Joseph form retains symmetry/positive semidefinite covariance.
            residual_map = np.tile(np.eye(2), (4, 1, 1))
            residual_map[:, :, 0] -= gain
            self.covariance = (
                residual_map @ self.covariance @ residual_map.transpose(0, 2, 1)
                + self.config.measurement_noise * gain[:, :, None] * gain[:, None, :]
            )
        self.box()

    def box(self) -> Box:
        if (
            not np.isfinite(self.position).all()
            or not np.isfinite(self.velocity).all()
            or not np.isfinite(self.covariance).all()
            or np.any(self.position[2:] <= 0)
        ):
            raise ValueError("Invalid image motion state")
        x, y, w, h = map(float, self.position)
        return Box(x - w / 2, y - h / 2, x + w / 2, y + h / 2)
