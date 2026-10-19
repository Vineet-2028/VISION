"""Text overlay data independent of a GUI. GUI rendering is an optional future adapter."""

from .contracts import FrameResult


class FrameInfoOverlay:
    def lines(
        self,
        result: FrameResult,
        mode: str,
        calibration_status: str,
        source_fps: float | None,
        processing_fps: float | None,
    ) -> tuple[str, ...]:
        latency_ns = result.timing.postprocess_completed_ns - result.timing.decode_started_ns
        lines: tuple[str, ...] = (
            f"Frame {result.identity.sequence} | observation {result.identity.observation_ns} ns",
            f"Mode {mode} | calibration {calibration_status}",
            f"Source FPS {source_fps} | processing FPS {processing_fps}",
            f"Decode-to-result {latency_ns} ns",
        )
        if result.depth is not None:
            lines += (
                f"Depth: {result.depth.representation.source} | "
                f"{result.depth.representation.unit} | EXACT_FRAME",
            )
            for index, estimate in enumerate(result.detection_depths[:8]):
                if estimate is not None:
                    lines += (
                        f"Object {index}: {estimate.value:.2f} {estimate.representation.unit} | "
                        f"{estimate.quality}",
                    )
        return lines
