"""Local field HTTP boundary. Inference runs behind a separate-process adapter."""

import hmac
import json
import socket
import ssl
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Any

from .clocks import processing_ns
from .field_export import export_session
from .field_pairing import PairingAuthority
from .field_protocol import (
    MAX_FRAME_BYTES,
    MAX_HEADER_BYTES,
    PROTOCOL,
    SessionStart,
    decode_frame,
    strict_json,
)
from .field_state import FieldSession, LatestSlot


class Gateway:
    def __init__(self, token: str, configuration_hash: str) -> None:
        if len(token) < 32 or not token.isascii():
            raise ValueError("Use an ephemeral token with at least 32 ASCII characters")
        self.token = token
        self.configuration_hash = configuration_hash
        self.session: FieldSession | None = None
        self.pending = LatestSlot()
        self.worker_status = "UNCONFIGURED"
        self.lock = threading.RLock()

    def dispatch(self, method: str, path: str, body: bytes, now: int) -> tuple[int, bytes, str]:
        if method == "GET" and path == "/v1/export":
            with self.lock:
                session = self.session
            if session is None:
                raise ValueError("NO_SESSION")
            # Pin the requested session; ZIP compression must never hold the admission lock.
            return 200, export_session(session, now), "application/zip"
        with self.lock:
            result: object = {}
            if self.session and self.session.expire_if_idle(now):
                self.pending.take()
            if method == "POST" and path == "/v1/session":
                start = SessionStart.model_validate(strict_json(body))
                if self.session and not self.session.closed:
                    raise ValueError("SESSION_ALREADY_ACTIVE")
                self.session = FieldSession(start, self.configuration_hash, now)
                self.pending = LatestSlot()
                result = {
                    "protocol_version": PROTOCOL,
                    "session_id": self.session.session_id,
                    "configuration_hash": self.configuration_hash,
                    "server_capabilities": [
                        "CLOCK_SYNC",
                        "LATEST_FRAME",
                        "STRUCTURED_EXPORT",
                        *(
                            ["GUARDIAN_WORKER", "FIELD_RESULT", "SPEECH_EVENTS"]
                            if self.worker_status != "UNCONFIGURED"
                            else []
                        ),
                    ],
                }
            elif method == "GET" and path in ("/v1/status", "/v1/alerts"):
                status: dict[str, object] = (
                    self.session.snapshot(now, alerts_only=path == "/v1/alerts")
                    if self.session
                    else {"status": "DISCONNECTED"}
                )
                status["worker_status"] = self.worker_status
                status["pending_replaced"] = self.pending.replaced
                result = status
            elif self.session is None:
                raise ValueError("NO_SESSION")
            elif method == "POST" and path == "/v1/close":
                if session_command(body, self.session):
                    raise ValueError("UNEXPECTED_CLOSE_FIELDS")
                self.session.close()
                self.pending.take()
            elif method == "POST" and path == "/v1/frame":
                header, image = decode_frame(body)
                capture = self.session.accept_frame(header, now)
                self.pending.put((self.session.session_id, header, image, capture))
                result = {"accepted": True, "sequence": header.sequence}
            elif method == "POST" and path == "/v1/sync/start":
                data = session_command(body, self.session)
                result = self.session.begin_sync(ns(data, "t0"), now, processing_ns())
            elif method == "POST" and path == "/v1/sync/finish":
                data = session_command(body, self.session)
                challenge = data.get("challenge")
                if not isinstance(challenge, str) or len(challenge) != 24:
                    raise ValueError("SYNC_CHALLENGE_INVALID")
                estimate = self.session.finish_sync(challenge, ns(data, "t3"), now)
                result = {
                    "version": estimate.version,
                    "offset_ns": str(estimate.offset_ns),
                    "uncertainty_ns": str(estimate.uncertainty_ns),
                    "rtt_ns": str(estimate.rtt_ns),
                }
            elif method == "POST" and path == "/v1/recording":
                data = session_command(body, self.session)
                if type(data.get("enabled")) is not bool or set(data) != {"enabled"}:
                    raise ValueError("RECORDING_BOOLEAN_REQUIRED")
                with self.session.lock:
                    if self.session.closed or self.session.recording_full:
                        raise ValueError("SESSION_RECORDING_UNAVAILABLE")
                    self.session.recording = bool(data["enabled"])
            elif method == "POST" and path == "/v1/event":
                data = session_command(body, self.session)
                if (
                    set(data) != {"kind", "scenario"}
                    or data["kind"] not in ("START_SCENARIO", "END_SCENARIO")
                    or data["scenario"]
                    not in (
                        "STATIC_OBSTACLE",
                        "PERSON_CROSSING",
                        "PARALLEL_PERSON",
                        "BICYCLE_PUSHED",
                        "CAMERA_TURN",
                        "LOW_LIGHT",
                        "CROWD",
                        "OTHER",
                    )
                ):
                    raise ValueError("SCENARIO_EVENT_INVALID")
                self.session.record(str(data["kind"]), now, {"scenario": data["scenario"]})
            elif method == "POST" and path == "/v1/speech-event":
                data = session_command(body, self.session)
                outputs = data.pop("available_outputs", [])
                if (
                    set(data) != {"kind", "alert_id", "client_ns"}
                    or not isinstance(outputs, list)
                    or len(outputs) > 5
                    or any(
                        v not in ("SPEAKER", "WIRED", "BLUETOOTH", "USB", "OTHER") for v in outputs
                    )
                ):
                    raise ValueError("INVALID_SPEECH_EVENT")
                self.session.record_speech(
                    str(data["kind"]),
                    str(data["alert_id"]),
                    ns(data, "client_ns"),
                    now,
                    tuple(outputs),
                )
            else:
                return 404, b'{"error":"NOT_FOUND"}', "application/json"
            return 200, json.dumps(result, allow_nan=False).encode(), "application/json"


def session_command(body: bytes, session: FieldSession) -> dict[str, object]:
    data = strict_json(body)
    if data.pop("session_id", None) != session.session_id:
        raise ValueError("WRONG_SESSION")
    return data


def ns(data: dict[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, str) or not value.isascii() or not value.isdigit():
        raise ValueError("TIMESTAMP_REQUIRED")
    if len(value) > 19 or not 0 <= int(value) < 2**63:
        raise ValueError("TIMESTAMP_RANGE")
    return int(value)


class FieldHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    block_on_close = True
    request_queue_size = 8

    def __init__(
        self,
        address: tuple[str, int],
        gateway: Gateway,
        tls: ssl.SSLContext | None = None,
        pairing: PairingAuthority | None = None,
    ) -> None:
        if address[0] not in ("127.0.0.1", "localhost") and tls is None:
            raise ValueError("LAN_REQUIRES_TLS")
        self.gateway = gateway
        self.pairing = pairing
        self.transport_errors = 0
        self.slots = threading.BoundedSemaphore(8)
        super().__init__(address, Handler)
        if tls:
            self.socket = tls.wrap_socket(
                self.socket, server_side=True, do_handshake_on_connect=False
            )

    def process_request(
        self, request: socket.socket | tuple[bytes, socket.socket], client_address: Any
    ) -> None:
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def handle_error(self, request: Any, client_address: Any) -> None:
        # TLS rejection is expected during pairing failures. Do not print addresses,
        # request bodies or credentials via socketserver's default traceback logger.
        with self.gateway.lock:
            self.transport_errors += 1

    def process_request_thread(
        self, request: socket.socket | tuple[bytes, socket.socket], client_address: Any
    ) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class Handler(BaseHTTPRequestHandler):
    server: FieldHTTPServer
    protocol_version = "HTTP/1.0"

    def setup(self) -> None:
        self.request.settimeout(2)
        super().setup()

    def log_message(self, format: str, *args: object) -> None:
        # No tokens, camera metadata, IP addresses, or user events in access logs.
        pass

    def respond(self, code: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        origin = self.headers.get("Origin")
        if origin in ("http://127.0.0.1:3000", "http://localhost:3000"):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.respond(204, b"")

    def do_GET(self) -> None:
        self.handle_api()

    def do_POST(self) -> None:
        self.handle_api()

    def handle_api(self) -> None:
        if self.path in ("/v1/pair", "/v1/session-token"):
            self.handle_pairing()
            return
        authorization = self.headers.get_all("Authorization", [])
        bearer = (
            authorization[0][7:]
            if len(authorization) == 1 and authorization[0].startswith("Bearer ")
            else ""
        )
        operator = hmac.compare_digest(bearer.encode(), self.server.gateway.token.encode())
        pairing = self.server.pairing
        session = self.server.gateway.session
        paired = pairing is not None and pairing.authorize(
            bearer, session.session_id if session else None
        )
        if not operator and not paired:
            self.respond(401, b'{"error":"UNAUTHORIZED"}')
            return
        origin = self.headers.get("Origin")
        if origin and origin not in ("http://127.0.0.1:3000", "http://localhost:3000"):
            self.respond(403, b'{"error":"ORIGIN_DENIED"}')
            return
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get("Transfer-Encoding") or len(lengths) > 1:
            self.respond(400, b'{"error":"AMBIGUOUS_BODY"}')
            return
        try:
            length = int(lengths[0]) if lengths else 0
            maximum = MAX_FRAME_BYTES + MAX_HEADER_BYTES + 4 if self.path == "/v1/frame" else 16384
            if not 0 <= length <= maximum:
                raise ValueError("BODY_SIZE")
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError("TRUNCATED_BODY")
            if paired and not operator and pairing is not None:
                # Serialize admission/binding: a token is usable for exactly one session.
                with self.server.gateway.lock, pairing.lock:
                    current = self.server.gateway.session
                    if not pairing.authorize(bearer, current.session_id if current else None):
                        raise ValueError("REVOKED")
                    if (
                        self.path == "/v1/session"
                        and pairing.grants[pairing.digest(bearer)].session_id is not None
                    ):
                        raise ValueError("NEW_SESSION_TOKEN_REQUIRED")
                    code, payload, content_type = self.server.gateway.dispatch(
                        self.command, self.path, body, processing_ns()
                    )
                    if self.path == "/v1/session" and code == 200:
                        assert self.server.gateway.session is not None
                        pairing.bind(bearer, self.server.gateway.session.session_id)
                    if self.path == "/v1/close":
                        pairing.release_session(bearer)
            else:
                code, payload, content_type = self.server.gateway.dispatch(
                    self.command, self.path, body, processing_ns()
                )
            self.respond(code, payload, content_type)
        except (ValueError, TypeError, KeyError, RecursionError):
            self.respond(400, b'{"error":"INVALID_REQUEST"}')
        except (OSError, TimeoutError):
            self.close_connection = True

    def handle_pairing(self) -> None:
        pairing = self.server.pairing
        if (
            pairing is None
            or not isinstance(self.connection, ssl.SSLSocket)
            or self.command != "POST"
            or self.headers.get("Origin")
        ):
            self.respond(403, b'{"error":"PAIRING_UNAVAILABLE"}')
            return
        try:
            lengths = self.headers.get_all("Content-Length", [])
            if len(lengths) != 1 or self.headers.get("Transfer-Encoding"):
                raise ValueError("LENGTH_REQUIRED")
            length = int(lengths[0])
            if not 0 < length <= 1024:
                raise ValueError("BODY_SIZE")
            data = strict_json(self.rfile.read(length))
            key = "code" if self.path == "/v1/pair" else "device_key"
            credential = data.get(key)
            if set(data) != {key} or not isinstance(credential, str) or len(credential) > 128:
                raise ValueError("INVALID_BOOTSTRAP")
            with self.server.gateway.lock:
                token = pairing.exchange(credential) if key == "code" else pairing.mint(credential)
                if self.server.gateway.session:
                    self.server.gateway.session.close()
                    self.server.gateway.pending.take()
            name = "device_key" if key == "code" else "token"
            self.respond(200, json.dumps({name: token}).encode())
        except (ValueError, TypeError, KeyError, RecursionError):
            self.respond(401, b'{"error":"PAIR_AGAIN"}')
        except (OSError, TimeoutError):
            self.close_connection = True
