"""Lifetime moments and exact nearest-rank quantiles of a bounded recent window."""

import math
from collections import deque
from typing import Any


class Distribution:
    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("Positive capacity required")
        self.samples: deque[int] = deque(maxlen=capacity)
        self.count = 0
        self.total = 0
        self.minimum: int | None = None
        self.maximum: int | None = None

    def add(self, value: int) -> None:
        if value < 0:
            raise ValueError("Negative duration")
        self.count += 1
        self.total += value
        self.minimum = value if self.minimum is None else min(value, self.minimum)
        self.maximum = value if self.maximum is None else max(value, self.maximum)
        self.samples.append(value)

    def summary(self) -> dict[str, Any]:
        ordered = sorted(self.samples)
        return {
            "count": self.count,
            "min_ns": self.minimum,
            "max_ns": self.maximum,
            "mean_ns": self.total / self.count if self.count else None,
            "percentile_scope": "recent_window",
            "window_count": len(ordered),
            **{
                f"p{q}_ns": ordered[math.ceil(q / 100 * len(ordered)) - 1] if ordered else None
                for q in (50, 90, 95, 99)
            },
        }


class Metrics:
    def __init__(self, capacity: int) -> None:
        self.counts = dict.fromkeys(
            ("source", "decoded", "accepted", "processed", "dropped", "failed"), 0
        )
        self.drops: dict[str, int] = {}
        self.stages = {
            key: Distribution(capacity)
            for key in (
                "decode",
                "conversion",
                "queue",
                "preprocess",
                "scheduler",
                "component",
                "postprocess",
                "result",
                "record",
                "render",
                "realtime_result_age",
                "realtime_detector_result_age",
                "tracking",
                "depth",
                "depth_sampling",
                "optical_flow",
                "ego_motion",
                "motion_compensation",
                "motion_track_sampling",
                "realtime_flow_result_age",
                "realtime_depth_result_age",
                "realtime_tracking_result_age",
            )
        }
        self.first_observation: int | None = None
        self.last_observation: int | None = None
        self.observations = 0

    def observe(self, ns: int) -> None:
        if self.first_observation is None:
            self.first_observation = ns
        self.last_observation = ns
        self.observations += 1

    def source_duration(self) -> int:
        if self.last_observation is None or self.first_observation is None:
            return 0
        return self.last_observation - self.first_observation

    def source_fps(self) -> float | None:
        duration = self.source_duration()
        return (self.observations - 1) * 1e9 / duration if duration > 0 else None

    def output_fps(self, elapsed_ns: int) -> float | None:
        return self.counts["processed"] * 1e9 / elapsed_ns if elapsed_ns > 0 else None

    def summary(self, elapsed_ns: int, peak_queue: int) -> dict[str, Any]:
        duration = (
            self.last_observation - self.first_observation
            if self.last_observation is not None and self.first_observation is not None
            else 0
        )
        return {
            "frame_counts": self.counts.copy(),
            "drops": self.drops.copy(),
            "source_duration_ns": duration,
            "source_fps": (self.observations - 1) * 1e9 / duration if duration > 0 else None,
            "decode_fps": self.counts["decoded"] * 1e9 / elapsed_ns if elapsed_ns > 0 else None,
            "processing_fps": self.counts["processed"] * 1e9 / elapsed_ns
            if elapsed_ns > 0
            else None,
            "effective_output_fps": self.counts["processed"] * 1e9 / elapsed_ns
            if elapsed_ns > 0
            else None,
            "elapsed_processing_ns": elapsed_ns,
            "peak_queue_depth": peak_queue,
            "timing": {key: value.summary() for key, value in self.stages.items()},
        }
