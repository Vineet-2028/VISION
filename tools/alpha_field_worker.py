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


def project(result, source, diagnostics=False):
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
    rejected = []

    def reject(item, reason):
        if diagnostics and len(rejected) < 32:
            rejected.append(
                {
                    "alert_id": item.alert_id if hasattr(item, "alert_id") else None,
                    "intent": compact_alpha(item.intent),
                    "reason": reason,
                }
            )

    for item in result.alert_output_set.outputs if result.alert_output_set else ():
        intent, presentation = item.intent, item.presentation
        if not item.delivered or intent is None or presentation is None or intent.lineage is None:
            reject(item, "UPSTREAM_NOT_DELIVERED_OR_MISSING_LINEAGE")
            continue
        if (
            intent.session_id != source.session_id
            or presentation.alert_id != intent.alert_id
            or presentation.lineage != intent.lineage
        ):
            reject(item, "SESSION_OR_PRESENTATION_LINEAGE_MISMATCH")
            continue
        original = intent.source_observation_ns
        host_source = next((host for pts, host in source.captures if pts == original), None)
        if host_source is None or original is None:
            reject(item, "SOURCE_CAPTURE_NOT_RETAINED")
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
        else:
            reject(item, "INVALID_STATE_OR_EXPIRED_DEADLINE")
    scene["field_alerts"] = speech
    if diagnostics:
        scene["gateway_rejections"] = rejected
    return scene


def object_diagnostics(result):
    """Link actual consumed records by exact entity IDs within one update."""
    state = result.world_state
    if state is None:
        return {"objects": [], "status": "WORLD_UNAVAILABLE"}
    decisions = result.attention_decision_set
    selected = decisions.selected if decisions else ()
    suppressed = decisions.suppressed if decisions else ()
    interactions = result.interaction_analysis
    risks = result.risk_assessment_set
    outputs = result.alert_output_set.outputs if result.alert_output_set else ()
    objects = []
    for entity in state.entities[:8]:
        attention = [d for d in selected if d.entity_id == entity.entity_id]
        rejected = [d for d in suppressed if d.decision.entity_id == entity.entity_id]
        alerts = [
            output
            for output in outputs
            if output.intent
            and output.intent.lineage
            and output.intent.lineage.entity_instance_id == entity.entity_id
            and output.intent.lineage.track_id == entity.source_track_id
        ]
        objects.append(
            {
                "entity_id": compact_alpha(entity.entity_id),
                "track_id": compact_alpha(entity.source_track_id),
                "track_generation": entity.source_track_id.serial,
                "box": compact_alpha(entity.image_geometry),
                "observation": compact_alpha(entity.entity_observation),
                "source_frame": compact_alpha(entity.entity_observation.source_frame)
                if entity.entity_observation
                else None,
                "semantics": compact_alpha(entity.track_semantics),
                "world_reasons": list(entity.reasons),
                "corridor": compact_alpha(
                    next(
                        (
                            relation
                            for relation in result.corridor_analysis.entity_relations
                            if relation.entity_id == entity.entity_id
                        ),
                        None,
                    )
                )
                if result.corridor_analysis
                else None,
                "interaction": compact_alpha(
                    next(
                        (
                            i
                            for i in interactions.entity_interactions
                            if i.entity_id == entity.entity_id
                        ),
                        None,
                    )
                )
                if interactions
                else None,
                "risk": compact_alpha(
                    next((r for r in risks.assessments if r.entity_id == entity.entity_id), None)
                )
                if risks
                else None,
                "attention": compact_alpha(attention),
                "suppressed": compact_alpha(rejected),
                "alerts": compact_alpha(alerts),
                "first_proven_loss_reason": "UNKNOWN",
                "first_confirmed_failure_stage": "UNKNOWN",
                "contributing_causes": list(entity.reasons),
                "unknown_evidence": [
                    "Independent physical target annotation",
                    "Acoustically heard output",
                ],
            }
        )
    payload = {"objects": objects, "truncated": len(state.entities) > 8}
    if len(json.dumps(payload).encode()) > 32_768:
        return {"objects": [], "status": "DIAGNOSTIC_BYTE_BUDGET_EXCEEDED"}
    return payload


def diagnostic_camera_main(pipe, session_id, width, height, profile, runtime):
    camera_main(pipe, session_id, width, height, profile, runtime, diagnostics=True)


def bounded_object_evidence(result, tracking, gateway_rejections):
    payload = object_diagnostics(result)
    payload["tracking"] = tracking
    payload["gateway_rejections"] = gateway_rejections
    dropped = {"objects": 0, "cost_observations": 0, "gateway_rejections": 0}
    # Keep useful partial evidence instead of discarding an oversized entire publication.
    payload["tracking"] = {
        **tracking,
        "cost_observations": list(tracking.get("cost_observations", [])),
    }
    for name, values in (
        ("cost_observations", payload["tracking"]["cost_observations"]),
        ("gateway_rejections", payload["gateway_rejections"]),
        ("objects", payload["objects"]),
    ):
        while values and len(json.dumps(payload).encode()) > 24_000:
            values.pop()
            dropped[name] += 1
    payload["budget_omissions"] = dropped
    return payload


def camera_main(pipe, session_id, width, height, profile, runtime, diagnostics=False):
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
                self.current = project(result, source, diagnostics)
                if diagnostics:
                    snapshot = detector.diagnostic
                    self.current["detector_diagnostics"] = snapshot
                    self.current["object_diagnostics"] = bounded_object_evidence(
                        result,
                        tracker.diagnostic if tracker else {"status": "NOT_OBSERVED"},
                        self.current.pop("gateway_rejections"),
                    )

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
        detector_type = PicoDetDetector
        if diagnostics:
            from perception_lab.field_detector_diagnostics import DiagnosticPicoDet

            detector_type = DiagnosticPicoDet
        detector = detector_type(
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
        tracker = None
        if diagnostics and config.tracker is not None:
            from perception_lab.field_tracking_diagnostics import DiagnosticTracker

            tracker = DiagnosticTracker(
                config.tracker,
                session_id,
                session_id,
                width,
                height,
                objectness_first=config.entity_semantics_ontology is not None,
            )
            tracker.diagnostic = {"status": "NOT_OBSERVED"}
        engine = CameraPipeline(
            config,
            build_preprocessor(geometry, config),
            recorder,
            detector=detector,
            segmentation=segmentation,
            motion_geometry=geometry,
            tracker=tracker,
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
