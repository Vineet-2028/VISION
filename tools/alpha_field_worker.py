"""Local camera adapter for the frozen Guardian engine. One IPC request per result."""

import json
from collections import deque
from pathlib import Path
from threading import Lock
from time import perf_counter_ns

from alpha_trace import compact_alpha


class CameraSource:
    def __init__(self, pipe, session_id):
        self.pipe, self.session_id = pipe, session_id
        self.origin = None
        self.captures = deque(maxlen=64)
        self.active = None
        self.send_lock = Lock()

    def send(self, reply):
        with self.send_lock:
            self.pipe.send(reply)

    def __iter__(self):
        import cv2
        import numpy as np

        from perception_lab.contracts import (
            Frame,
            FrameIdentity,
            PixelFormat,
            TimingProvenance,
        )
        from perception_lab.field_orientation import field_orientation
        from perception_lab.field_protocol import FrameHeader, check_camera_jpeg

        while True:
            self.send(("REQUEST",))
            packet = self.pipe.recv()
            if packet is None:
                return
            data, jpeg, captured = packet
            header = FrameHeader.model_validate(data)
            if header.session_id != self.session_id:
                raise ValueError("WRONG_CAPTURE_SESSION")
            now = perf_counter_ns()
            if not 0 <= now - captured < 500_000_000:
                self.send(("EXPIRED", header.sequence))
                continue
            check_camera_jpeg(jpeg, header.width, header.height)
            pixels = cv2.imdecode(
                np.frombuffer(jpeg, np.uint8),
                cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION,
            )
            if pixels is None or pixels.shape != (header.height, header.width, 3):
                self.send(("INVALID_IMAGE", header.sequence))
                continue
            stamp = int(header.camera_ns)
            if self.origin is None:
                self.origin = stamp
            observation = stamp - self.origin
            identity = FrameIdentity(
                self.session_id,
                header.sequence,
                observation,
                TimingProvenance.AUTHORITATIVE_PTS,
            )
            orientation = field_orientation(identity, header)
            self.active = header.sequence, captured
            self.captures.append((observation, captured))
            yield Frame(
                identity,
                pixels,
                PixelFormat.BGR,
                now,
                perf_counter_ns(),
                camera_orientation=orientation,
            )

    def close(self):
        pass  # The process entry point owns the connection.


def project(result, source):
    observation = result.identity.observation_ns
    _, captured = source.active
    world = result.world_state
    scene = {
        "schema_version": 1,
        "mode": "REALTIME",
        "source_type": "LIVE_CAMERA",
        "source_clock": "CAMERA_REALTIME_RELATIVE_TO_FIRST_CAPTURE",
        "frame": compact_alpha(result.identity),
        "dimensions": {"width": result.width, "height": result.height},
        "source_to_publication_age_ns": perf_counter_ns() - captured,
        "world": None
        if world is None
        else {
            "entities": [
                {
                    "entity_id": compact_alpha(e.entity_id),
                    "source_track_id": compact_alpha(e.source_track_id),
                    "track_semantics": compact_alpha(e.track_semantics),
                    "category": e.category,
                    "box": compact_alpha(e.image_geometry),
                    "observation_status": e.observation_status,
                }
                for e in world.entities
            ],
            "scene_quality": compact_alpha(world.scene_quality),
        },
        "camera_orientation": compact_alpha(result.camera_orientation),
        "camera_view_quality": compact_alpha(result.camera_view_quality),
        "heading": compact_alpha(result.user_motion_heading),
        "provider_state": {"scene_capability": result.scene_capability},
        "errors": list(result.errors),
        "warnings": list(result.warnings),
    }
    for key, field in (
        ("detector", "detector"),
        ("tracks", "tracks"),
        ("corridor", "corridor_analysis"),
        ("trajectory", "trajectory_set"),
        ("interaction", "interaction_analysis"),
        ("risk", "risk_assessment_set"),
        ("attention", "attention_decision_set"),
        ("alerts", "alert_output_set"),
    ):
        scene[key] = compact_alpha(getattr(result, field))
    speech = []
    for item in result.alert_output_set.outputs if result.alert_output_set else ():
        intent, presentation = item.intent, item.presentation
        if not item.delivered or intent is None or presentation is None or intent.lineage is None:
            continue
        if (
            intent.session_id != source.session_id
            or presentation.alert_id != intent.alert_id
            or presentation.lineage != intent.lineage
        ):
            continue
        original = intent.source_observation_ns
        host_source = next((host for pts, host in source.captures if pts == original), None)
        if host_source is None or original is None:
            continue
        deadline = min(
            host_source + 500_000_000,
            captured + presentation.valid_until_ns - observation,
        )
        state = captured + intent.state_timestamp - observation
        if host_source <= state < deadline and perf_counter_ns() < deadline:
            speech.append(
                {
                    "session_id": source.session_id,
                    "alert_id": intent.alert_id,
                    "text": presentation.speech_text,
                    "reason_codes": list(intent.reason_codes),
                    "semantic_level": intent.semantic_level,
                    "source_host_ns": str(host_source),
                    "source_camera_ns": str(source.origin + original),
                    "state_host_ns": str(state),
                    "deadline_host_ns": str(deadline),
                }
            )
    scene["field_alerts"] = speech
    return scene


def camera_main(pipe, session_id, width, height, profile, runtime):
    from rescue_runtime import activate_onnx

    handles = []
    try:
        _, handles = activate_onnx(*map(Path, runtime))
        from perception_lab.config import Calibration, LabConfig
        from perception_lab.edge_runtime import PicoDetDetector
        from perception_lab.geometry import CoreGeometry
        from perception_lab.orientation_preprocessing import build_preprocessor
        from perception_lab.pipeline import Pipeline
        from perception_lab.recording import SessionRecorder
        from perception_lab.semantic_runtime import OnnxSemanticSegmenter

        config = LabConfig.model_validate(
            {
                **profile,
                "source_id": session_id,
                "start_ns": 0,
                "end_ns": None,
                "record_session": False,
                "visualization": False,
            }
        )
        cal = json.loads(Path(config.calibration).read_text())
        if cal["calibration_quality"]["state"] != "UNKNOWN":
            raise ValueError("A recorded calibration cannot be transplanted to the phone")
        cal.update(camera_id="field-camera", resolution={"width": width, "height": height})
        calibration = Calibration.model_validate(cal)
        geometry = CoreGeometry(calibration)
        source = CameraSource(pipe, session_id)

        class Recorder(SessionRecorder):
            current = None

            def write_result(self, result):
                self.current = project(result, source)

        class CameraPipeline(Pipeline):
            def accept(self, frame, due_ns):
                sequence, captured = source.active
                if sequence != frame.identity.sequence:
                    raise ValueError("Field frame lost its capture identity")
                # The replay scheduler's due time must never refresh a camera observation.
                super().accept(frame, captured)

            def process(self, item):
                recorder.current = None
                super().process(item)
                sequence, captured = source.active
                if recorder.current is None or perf_counter_ns() - captured >= 500_000_000:
                    source.send(("EXPIRED", sequence))
                elif len(json.dumps(recorder.current).encode()) > 900_000:
                    source.send(("RESULT_TOO_LARGE", sequence))
                else:
                    source.send(("RESULT", sequence, captured, recorder.current))

        recorder = Recorder(config, calibration, Path("."))
        recorder.session_id = session_id
        recorder.manifest.update(session_id=session_id, source_type="LIVE_CAMERA")
        d = config.detector
        detector = PicoDetDetector(
            Path(d.weights),
            d.sha256,
            size=d.input_size,
            confidence=d.confidence,
            device=d.device,
            half=d.half,
            threads=d.threads,
        )
        detector.enable_entity_semantics(Path(config.entity_semantics_ontology))
        segmentation = OnnxSemanticSegmenter(config.segmentation, Path("."), session_id)
        engine = CameraPipeline(
            config,
            build_preprocessor(geometry, config),
            recorder,
            detector=detector,
            segmentation=segmentation,
            motion_geometry=geometry,
        )
        pipe.send(("READY",))
        try:
            engine.run(source)
        finally:
            recorder.close()
    except (EOFError, BrokenPipeError):
        pass
    except Exception as error:
        pipe.send(("FAILED", type(error).__name__))
    finally:
        for handle in handles:
            handle.close()
        pipe.close()
