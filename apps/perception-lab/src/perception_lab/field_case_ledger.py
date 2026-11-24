"""Offline evidence references, never an inferred physical-object success chain."""

from typing import Any


def case_ledger(packet: dict[str, Any], session: str) -> dict[str, Any]:
    """Bound references to existing records; preserve publication/source clocks.

    A present result is not proof that a reference object survived a stage.
    No model execution, class inference, or threshold decisions happen here.
    """
    stages = {
        name: {"availability": "EVIDENCE_NOT_AVAILABLE", "references": []}
        for name in (
            "CAPTURE",
            "ADMISSION",
            "ORIENTATION",
            "DETECTOR_SOURCE",
            "POST_VENDOR",
            "FILTERING",
            "PRE_NMS",
            "TRACK_ASSOCIATION",
            "TRACK_GENERATION",
            "SEMANTICS",
            "WORLD",
            "CORRIDOR",
            "INTERACTION",
            "RISK",
            "ATTENTION",
            "ALERT_INTENT",
            "GATEWAY_RESULT",
            "PHONE_RECEIPT",
            "TTS_REQUEST",
            "TTS_CALLBACK",
        )
    }
    omitted = 0

    def add(stage: str, pointer: str) -> None:
        nonlocal omitted
        refs = stages[stage]["references"]
        assert isinstance(refs, list)
        if len(refs) < 16:
            refs.append(pointer)
            stages[stage]["availability"] = "RECORDED_EVIDENCE_NOT_PROOF_OF_SUCCESS"
        else:
            omitted += 1

    add("CAPTURE", "/jpeg_sha256")
    for collection in ("recorded_events", "detector_source_events"):
        for i, event in enumerate(packet.get(collection, [])):
            base = f"/{collection}/{i}"
            if event.get("kind") == "FRAME_ADMITTED":
                add("ADMISSION", base)
                if event.get("rotation") == packet["rotation"]:
                    add("ORIENTATION", base + "/rotation")
            detector = event.get("detector_diagnostics")
            if isinstance(detector, dict) and (
                detector.get("source_id") == session
                and detector.get("source_sequence") == packet["sequence"]
            ):
                for stage in ("DETECTOR_SOURCE", "POST_VENDOR", "FILTERING"):
                    add(stage, base + "/detector_diagnostics")
            evidence = event.get("object_diagnostics") or {}
            for j, obj in enumerate(evidence.get("objects", [])[:8]):
                source = obj.get("source_frame") or {}
                if (
                    source.get("source_id") != session
                    or source.get("sequence") != packet["sequence"]
                ):
                    continue
                pointer = base + f"/object_diagnostics/objects/{j}"
                for stage, field in (
                    ("TRACK_GENERATION", "track_id"),
                    ("SEMANTICS", "semantics"),
                    ("WORLD", "entity_id"),
                    ("CORRIDOR", "corridor"),
                    ("INTERACTION", "interaction"),
                    ("RISK", "risk"),
                    ("ATTENTION", "attention"),
                    ("ATTENTION", "suppressed"),
                    ("ALERT_INTENT", "alerts"),
                ):
                    if obj.get(field):
                        add(stage, pointer + "/" + field)
            tracking = evidence.get("tracking") or {}
            if (
                tracking.get("source_id") == session
                and tracking.get("source_sequence") == packet["sequence"]
            ):
                add("TRACK_ASSOCIATION", base + "/object_diagnostics/tracking")
            if event.get("alerts"):
                add("GATEWAY_RESULT", base + "/alerts")
    for i, event in enumerate(packet.get("delivery_events", [])):
        kind = event.get("kind")
        callback_stage = {
            "PHONE_RESULT_RECEIVED": "PHONE_RECEIPT",
            "TTS_SUBMITTED": "TTS_REQUEST",
            "TTS_BEGIN_SYNTHESIS": "TTS_CALLBACK",
            "APP_TTS_PLAYBACK_START_ESTIMATE": "TTS_CALLBACK",
            "TTS_ERROR": "TTS_CALLBACK",
            "TTS_COMPLETED": "TTS_CALLBACK",
        }.get(kind)
        if callback_stage:
            add(callback_stage, f"/delivery_events/{i}")
    return {
        "schema": "vision.field.causal-references.v1",
        "session_id": session,
        "capture_sequence": packet["sequence"],
        "camera_ns": packet["camera_ns"],
        "clock_domain": "ANDROID_ELAPSED_REALTIME",
        "stage_source_timestamps": "Use referenced source identity, not publication time",
        "model_configuration_provenance": "Read referenced detector and exported gateway manifest",
        "first_confirmed_failure_stage": "UNKNOWN",
        "reference_object_identity": "NO_REFERENCE_OBJECT_IDENTITY",
        "contributing_reasons": "Read referenced records; suppression is not necessarily a defect",
        "acoustic_output": "EVIDENCE_NOT_AVAILABLE",
        "references_omitted": omitted,
        "stages": stages,
    }
