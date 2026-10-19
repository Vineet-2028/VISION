"""Local-only command-line entry point. Public errors never contain input paths."""

import argparse
import json
import sys
from pathlib import Path

from .config import Calibration, LabConfig, read_json
from .contracts import Cancellation
from .detector_runtime import UltralyticsDetector
from .edge_runtime import PicoDetDetector, YoloXDetector
from .geometry import CoreGeometry
from .pipeline import Pipeline
from .preprocessing import BasicPreprocessor
from .recording import SessionRecorder
from .rtdetr_runtime import RtDetrDetector
from .sources import VideoFileSource
from .visualization import TkRenderer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="perception-lab", description="Local headless perception replay laboratory"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    replay = commands.add_parser("replay", help="Replay video with configured local components")
    replay.add_argument("--config", type=Path, required=True)
    replay.add_argument("--input")
    replay.add_argument("--calibration")
    replay.add_argument("--output")
    replay.add_argument("--record-session", action="store_true", default=None)
    replay.add_argument("--headless", action="store_true", help="Headless is the default")
    replay.add_argument("--start", type=int, help="Inclusive observation timestamp in nanoseconds")
    replay.add_argument("--end", type=int, help="Exclusive observation timestamp in nanoseconds")
    inspect = commands.add_parser("inspect", help="Inspect a pixel with guardian-core geometry")
    inspect.add_argument("--calibration", type=Path, required=True)
    inspect.add_argument("--u", type=float, required=True)
    inspect.add_argument("--v", type=float, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            calibration = Calibration.model_validate(read_json(args.calibration))
            print(json.dumps(CoreGeometry(calibration).inspect(args.u, args.v), allow_nan=False))
            return 0
        raw = read_json(args.config)
        for key in ("input", "calibration", "output", "record_session"):
            if getattr(args, key) is not None:
                raw[key] = getattr(args, key)
        if args.start is not None:
            raw["start_ns"] = args.start
        if args.end is not None:
            raw["end_ns"] = args.end
        if args.headless:
            raw["visualization"] = False
        config = LabConfig.model_validate(raw)
        # All relative paths (including overrides) resolve against the config's directory.
        base = args.config.resolve().parent
        calibration = Calibration.model_validate(read_json(base / config.calibration))
        geometry = CoreGeometry(calibration, source_scaling=config.source_scaling)
        preprocessor = BasicPreprocessor(geometry, config.preprocess)
        detector: UltralyticsDetector | RtDetrDetector | YoloXDetector | PicoDetDetector | None = (
            None
        )
        if config.detector is not None:
            d = config.detector
            factories: dict[
                str,
                type[UltralyticsDetector]
                | type[RtDetrDetector]
                | type[YoloXDetector]
                | type[PicoDetDetector],
            ] = {
                "rtdetr": RtDetrDetector,
                "ultralytics": UltralyticsDetector,
                "yolox": YoloXDetector,
                "picodet": PicoDetDetector,
            }
            factory = factories[d.runtime]
            detector = factory(
                base / d.weights,
                d.sha256,
                size=d.input_size,
                confidence=d.confidence,
                device=d.device,
                half=d.half,
                threads=d.threads,
            )
        from .depth_runtime import DepthAnythingProvider
        from .depth_synthetic import SyntheticDepthProvider

        depth = None
        if config.depth is not None:
            depth = (
                SyntheticDepthProvider(config.depth.synthetic_meters)
                if config.depth.provider == "synthetic"
                else DepthAnythingProvider(config.depth, base)
            )
        source = VideoFileSource(base / config.input, config.source_id, config.max_pixels)
        try:
            recorder = SessionRecorder(config, calibration, base / config.output)
        except BaseException:
            source.close()
            raise
        cancel = Cancellation()
        try:
            renderer = (
                TkRenderer(cancel, config.mode, calibration.calibration_quality.state)
                if config.visualization
                else None
            )
        except BaseException:
            source.close()
            recorder.finish({}, "FATAL", "RENDERER_OPEN_FAILED")
            raise
        try:
            pipeline = Pipeline(
                config,
                preprocessor,
                recorder,
                renderer=renderer,
                detector=detector,
                depth=depth,
                motion_geometry=geometry,
            )
        except BaseException:
            source.close()
            if renderer is not None:
                renderer.close()
            recorder.finish({}, "FATAL", "PIPELINE_OPEN_FAILED")
            raise
        manifest = pipeline.run(source, cancel)
        print(
            json.dumps(
                {
                    "session_id": manifest["session_id"],
                    "termination_reason": manifest["termination_reason"],
                    **manifest["summary"],
                },
                sort_keys=True,
                allow_nan=False,
                indent=2,
            )
        )
        return 0
    except KeyboardInterrupt:
        print("CANCELLED", file=sys.stderr)
        return 130
    except Exception:
        # Native decoder/JVM/Pydantic errors can carry private paths or configuration values.
        print(
            "LAB_FAILED: check source, calibration, configuration and session status.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
