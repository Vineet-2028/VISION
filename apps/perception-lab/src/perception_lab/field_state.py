"""Bounded, authenticated-session state independent of HTTP and model runtimes."""

import json
import secrets
from collections import Counter, deque
from copy import deepcopy
from threading import RLock

from .field_diagnostics import stage_ledger
from .field_protocol import ClockEstimate, FrameHeader, SessionStart, estimate_clock

CLIENT_TIMEOUT_NS = 3_000_000_000
MAX_RECORDED_EVENT_BYTES = 8 * 1024 * 1024


class FieldSession:
    def __init__(self, start: SessionStart, configuration_hash: str, now_ns: int) -> None:
        if (
            start.mode == "ANDROID_FIELD_HARNESS"
            and "CAMERA_REALTIME_CLOCK" not in start.capabilities
        ):
            raise ValueError("CAMERA_CLOCK_UNAVAILABLE")
        self.start = start
        self.session_id = secrets.token_hex(16)
        self.configuration_hash = configuration_hash
        self.started_ns = self.last_client_ns = now_ns
        self.last_sequence = self.last_capture_ns = -1
        self.last_host_capture_ns = -1
        self.lock = RLock()
        self.challenges: dict[str, tuple[int, int, int]] = {}
        self.estimates: deque[ClockEstimate] = deque(maxlen=8)
        self.sync_version = 0
        self.counts: Counter[str] = Counter()
        self.events: deque[dict[str, object]] = deque(maxlen=10_000)
        self.recording = False
        self.recording_full = False
        self.recorded_event_bytes = 0
        self._latest: tuple[int, int, dict[str, object]] | None = None
        self._admitted_captures: deque[tuple[int, int]] = deque(maxlen=8)
        self._worker_capture: tuple[int, int] | None = None
        self._speech_ids: deque[tuple[str, int | None]] = deque(maxlen=128)
        self._speech_events: deque[tuple[str, str]] = deque(maxlen=1024)
        self.closed = False

    def begin_sync(self, t0: int, t1: int, t2: int) -> dict[str, object]:
        with self.lock:
            if self.closed or t0 < 0 or t2 < t1:
                raise ValueError("SESSION_OR_CLOCK_INVALID")
            if len(self.challenges) >= 8:
                del self.challenges[next(iter(self.challenges))]
            challenge = secrets.token_hex(12)
            self.challenges[challenge] = t0, t1, t2
            return {"challenge": challenge, "t0": str(t0), "t1": str(t1), "t2": str(t2)}

    def finish_sync(self, challenge: str, t3: int, now_ns: int) -> ClockEstimate:
        with self.lock:
            if self.closed or challenge not in self.challenges:
                raise ValueError("SYNC_CHALLENGE_UNKNOWN")
            t0, t1, t2 = self.challenges.pop(challenge)
            if now_ns - t2 > 2_000_000_000:
                raise ValueError("SYNC_CHALLENGE_EXPIRED")
            self.sync_version += 1
            estimate = estimate_clock(t0, t1, t2, t3, self.sync_version)
            self.estimates.append(estimate)
            self.last_client_ns = now_ns
            return estimate

    def accept_frame(self, header: FrameHeader, now_ns: int) -> int:
        with self.lock:
            self.counts["frames_received"] += 1
            if self.closed or header.session_id != self.session_id:
                raise ValueError("WRONG_SESSION")
            if (header.width, header.height) != (self.start.width, self.start.height):
                raise ValueError("FRAME_DIMENSIONS_CHANGED")
            if (
                header.sequence <= self.last_sequence
                or int(header.camera_ns) <= self.last_capture_ns
            ):
                raise ValueError("REPLAYED_OR_OUT_OF_ORDER_FRAME")
            estimate = next((e for e in self.estimates if e.version == header.sync_version), None)
            if estimate is None:
                raise ValueError("SYNC_VERSION_UNKNOWN")
            capture = estimate.earliest_host_capture(int(header.camera_ns), now_ns)
            if capture <= self.last_host_capture_ns:
                raise ValueError("MAPPED_CAPTURE_REGRESSED")
            # Transport admission budget equals frozen risk/alert freshness, never extends it.
            if now_ns - capture >= 500_000_000:
                self.counts["frames_expired"] += 1
                raise ValueError("FRAME_EXPIRED")
            self.last_sequence, self.last_capture_ns = header.sequence, int(header.camera_ns)
            self.last_host_capture_ns = capture
            self._admitted_captures.append((header.sequence, capture))
            self.last_client_ns = now_ns
            self.record(
                "FRAME_ADMITTED",
                now_ns,
                {
                    "sequence": header.sequence,
                    "capture_host_ns": str(capture),
                    "camera_ns": header.camera_ns,
                    "capture_to_receive_ns": str(now_ns - capture),
                    "clock_uncertainty_ns": str(estimate.uncertainty_at(now_ns)),
                    "sync_version": header.sync_version,
                    "rotation": header.rotation,
                    "sensors": header.sensors.model_dump()
                    if header.sensors and self.recording
                    else None,
                },
            )
            return capture

    def begin_inference(self, sequence: int, captured: int) -> None:
        with self.lock:
            if (
                self.closed
                or self._worker_capture is not None
                or (sequence, captured) not in self._admitted_captures
            ):
                raise ValueError("INVALID_WORKER_CAPTURE")
            self._worker_capture = sequence, captured

    def end_inference(self) -> None:
        with self.lock:
            self._worker_capture = None

    def publish_result(
        self,
        *,
        session_id: str,
        sequence: int,
        capture_host_ns: int,
        scene: dict[str, object],
        now_ns: int,
    ) -> None:
        """Publish only a fresh result for an actual admitted capture in this session."""
        with self.lock:
            if self.closed or session_id != self.session_id:
                raise ValueError("WRONG_SESSION")
            if (sequence, capture_host_ns) != self._worker_capture and (
                sequence,
                capture_host_ns,
            ) not in self._admitted_captures:
                raise ValueError("RESULT_CAPTURE_NOT_ADMITTED")
            if self._latest is not None and sequence <= self._latest[0]:
                raise ValueError("RESULT_REPLAYED_OR_OUT_OF_ORDER")
            if not 0 <= now_ns - capture_host_ns < 500_000_000:
                raise ValueError("RESULT_EXPIRED_OR_FUTURE")
            self._latest = sequence, capture_host_ns, deepcopy(scene)
            alerts = scene.get("field_alerts")
            if isinstance(alerts, list):
                for alert in alerts:
                    if isinstance(alert, dict) and isinstance(alert.get("alert_id"), str):
                        stamp = alert.get("source_camera_ns")
                        self._speech_ids.append(
                            (
                                alert["alert_id"],
                                int(stamp)
                                if isinstance(stamp, str) and stamp.isdecimal()
                                else None,
                            )
                        )
            if not self.recording:
                self.counts["RESULT_PUBLISHED"] += 1
                return
            world = scene.get("world")
            diagnostic = scene.get("object_diagnostics")
            diagnostic_size = len(json.dumps(diagnostic).encode())
            used = getattr(self, "_diagnostic_bytes", 0)
            if diagnostic_size > 32_768 or used + diagnostic_size > 4 * 1024 * 1024:
                diagnostic = {"objects": [], "status": "SESSION_DIAGNOSTIC_BUDGET_EXCEEDED"}
            else:
                self._diagnostic_bytes = used + diagnostic_size
            entities = world.get("entities", []) if isinstance(world, dict) else []
            self.record(
                "RESULT_PUBLISHED",
                now_ns,
                {
                    "sequence": sequence,
                    "capture_to_publication_ns": str(now_ns - capture_host_ns),
                    "camera_orientation": scene.get("camera_orientation"),
                    "heading": scene.get("heading"),
                    "view": scene.get("camera_view_quality"),
                    "provider_state": scene.get("provider_state"),
                    "diagnostics": stage_ledger(scene, self.session_id, sequence),
                    "detector_diagnostics": scene.get("detector_diagnostics"),
                    "object_diagnostics": diagnostic,
                    "entities": [e.get("entity_id") for e in entities if isinstance(e, dict)][:128],
                    "alerts": alerts if isinstance(alerts, list) else [],
                },
            )

    def record_speech(
        self,
        kind: str,
        alert_id: str,
        client_ns: int,
        now_ns: int,
        available_outputs: tuple[str, ...] = (),
    ) -> None:
        with self.lock:
            known = dict(self._speech_ids)
            if alert_id not in known or kind not in {
                "PHONE_RESULT_RECEIVED",
                "TTS_BEGIN_SYNTHESIS",
                "TTS_SUBMITTED",
                "APP_TTS_PLAYBACK_START_ESTIMATE",
                "TTS_COMPLETED",
                "TTS_ERROR",
                "TTS_STOPPED",
                "TTS_CALLBACK_IGNORED_SUPERSEDED",
                "TTS_START_REJECTED_EXPIRED",
            }:
                raise ValueError("UNRECOGNIZED_SPEECH_EVENT")
            if (alert_id, kind) in self._speech_events:
                return
            origin = known[alert_id]
            if origin is not None and client_ns < origin:
                raise ValueError("CALLBACK_PRECEDES_CAPTURE")
            self.record(
                kind,
                now_ns,
                {
                    "alert_id": alert_id,
                    "client_event_ns": str(client_ns),
                    "capture_to_callback_ns": str(client_ns - origin)
                    if origin is not None
                    else None,
                    "available_outputs": list(available_outputs),
                    "physical_route": "UNVERIFIED",
                },
            )
            self._speech_events.append((alert_id, kind))

    def record(self, kind: str, timestamp_ns: int, details: dict[str, object]) -> None:
        with self.lock:
            if self.closed:
                raise ValueError("SESSION_CLOSED")
            self.counts[kind] += 1
            if self.recording:
                event = {**deepcopy(details), "kind": kind, "host_ns": str(timestamp_ns)}
                event_bytes = len(json.dumps(event).encode("utf-8")) + 1
                if (
                    len(self.events) == self.events.maxlen
                    or self.recorded_event_bytes + event_bytes > MAX_RECORDED_EVENT_BYTES
                ):
                    self.recording_full = True
                    self.recording = False
                else:
                    self.events.append(event)
                    self.recorded_event_bytes += event_bytes

    def snapshot(self, now_ns: int, *, alerts_only: bool = False) -> dict[str, object]:
        with self.lock:
            disconnected = self.closed or now_ns - self.last_client_ns > CLIENT_TIMEOUT_NS
            result: dict[str, object] | None = None
            result_status = "DISCONNECTED" if disconnected else "NO_RESULT"
            if not disconnected and self._latest is not None:
                sequence, captured, scene = self._latest
                age = now_ns - captured
                result_status = "FRESH" if 0 <= age < 500_000_000 else "EXPIRED_OR_FUTURE"
                if result_status == "FRESH":
                    result = {
                        "sequence": sequence,
                        "age_at_response_ns": str(age),
                    }
                    if alerts_only:
                        result["field_alerts"] = deepcopy(scene.get("field_alerts", []))
                    else:
                        result["scene"] = deepcopy(scene)
            return {
                "session_id": self.session_id,
                "mode": self.start.mode,
                "status": "DISCONNECTED" if disconnected else "CONNECTED",
                "duration_ns": str(max(0, now_ns - self.started_ns)),
                "recording": self.recording,
                "recording_full": self.recording_full,
                "counts": dict(self.counts),
                "result": result,
                "result_status": result_status,
            }

    def expire_if_idle(self, now_ns: int) -> bool:
        with self.lock:
            if self.closed or now_ns - self.last_client_ns <= CLIENT_TIMEOUT_NS:
                return False
            self.close()
            return True

    def close(self) -> None:
        with self.lock:
            self.closed = True
            self.recording = False
            self._latest = None
            self._admitted_captures.clear()
            self._worker_capture = None
            self._speech_ids.clear()
            self._speech_events.clear()
            self.challenges.clear()
            self.estimates.clear()


class LatestSlot:
    """One replaceable value; caller owns execution and failure propagation."""

    def __init__(self) -> None:
        self.lock = RLock()
        self.pending: object | None = None
        self.replaced = 0

    def put(self, value: object) -> None:
        with self.lock:
            self.replaced += self.pending is not None
            self.pending = value

    def take(self) -> object | None:
        with self.lock:
            value, self.pending = self.pending, None
            return value
