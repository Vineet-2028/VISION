"""Bounded shadow diagnostics; missing stage evidence never establishes a miss."""

from enum import StrEnum


class LossReason(StrEnum):
    OUTSIDE_CAMERA_FOV = "OUTSIDE_CAMERA_FOV"
    CAMERA_UNUSABLE = "CAMERA_UNUSABLE"
    FRAME_NOT_ADMITTED = "FRAME_NOT_ADMITTED"
    SOURCE_STALE = "SOURCE_STALE"
    DETECTOR_NO_CANDIDATE = "DETECTOR_NO_CANDIDATE"
    BELOW_DETECTOR_SCORE = "BELOW_DETECTOR_SCORE"
    NMS_SUPPRESSED = "NMS_SUPPRESSED"
    CAP_SUPPRESSED = "CAP_SUPPRESSED"
    TRACK_REJECTED = "TRACK_REJECTED"
    TRACK_REPLACED = "TRACK_REPLACED"
    SEMANTIC_UNSTABLE = "SEMANTIC_UNSTABLE"
    SEMANTIC_EXPIRED = "SEMANTIC_EXPIRED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    WORLD_GEOMETRY_UNAVAILABLE = "WORLD_GEOMETRY_UNAVAILABLE"
    HEADING_UNKNOWN = "HEADING_UNKNOWN"
    OUTSIDE_CORRIDOR = "OUTSIDE_CORRIDOR"
    INTERACTION_NOT_ESTABLISHED = "INTERACTION_NOT_ESTABLISHED"
    RISK_INSUFFICIENT = "RISK_INSUFFICIENT"
    ATTENTION_SUPPRESSED_WITH_REASON = "ATTENTION_SUPPRESSED_WITH_REASON"
    ALERT_EXPIRED = "ALERT_EXPIRED"
    PHONE_DISCONNECTED = "PHONE_DISCONNECTED"
    DEDUPLICATED = "DEDUPLICATED"
    TTS_FAILURE = "TTS_FAILURE"
    UNKNOWN = "UNKNOWN"


STAGES = (
    ("CAMERA_CAPTURE", "frame"),
    ("PREPROCESS_ROTATION", "camera_orientation"),
    ("FRAME_ADMISSION", None),
    ("DETECTOR_RAW_CANDIDATES", None),
    ("SCORE_GATE", None),
    ("NMS_CANDIDATE_CAP", None),
    ("TRACK_ASSOCIATION_GENERATION", "tracks"),
    ("SEMANTIC_EVIDENCE_FUSION_GROUP", None),
    ("WORLD_CORRIDOR", "corridor"),
    ("TRAJECTORY_INTERACTION", "interaction"),
    ("RISK", "risk"),
    ("ATTENTION", "attention"),
    ("ALERT_INTENT", "alerts"),
    ("PRESENTATION_EXPIRY", "field_alerts"),
    ("PHONE_RECEIVE_TTS", None),
    ("TTS_CALLBACK", None),
)


def stage_ledger(scene: dict[str, object], session_id: str, sequence: int) -> dict[str, object]:
    """Presence means a stage result exists, never that a target survived it.

    This projection retains no images, free text, boxes or unbounded arrays.
    Caller must gate persistence on explicit diagnostic recording consent.
    """
    return {
        "schema": "vision.field.stage-ledger.v1",
        "candidate": "ALPHA_V1_1_DIAGNOSTICS",
        "event_id": f"{session_id}:{sequence}:publication",
        "session_id": session_id,
        "sequence": sequence,
        "first_proven_loss_reason": LossReason.UNKNOWN.value,
        "stages": [
            {
                "stage": stage,
                "evidence": "RESULT_AVAILABLE"
                if field is not None and scene.get(field) is not None
                else "NOT_OBSERVED",
            }
            for stage, field in STAGES
        ],
    }
