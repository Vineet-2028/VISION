"""Serve the frozen local Guardian engine to a single authenticated field session."""

import argparse
import hashlib
import json
import multiprocessing
import secrets
import ssl
import threading
from pathlib import Path
from time import monotonic, perf_counter_ns

import psutil
from alpha_field_worker import camera_main

from perception_lab.field_gateway import FieldHTTPServer, Gateway


def hash_file(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def release_profile(manifest):
    release = json.loads(manifest.read_text())
    if release["release"] != "VISION_CONTROLLED_ALPHA_V1":
        raise ValueError("Frozen VISION Controlled Alpha V1 required")
    profile = release["configuration"]
    root = Path(__file__).resolve().parents[1]
    for name, expected in release["runtime_sources"].items():
        if name.startswith("tools/") or Path(name).name.startswith("field_"):
            continue
        if hash_file(root / name) != expected:
            raise ValueError(f"Frozen runtime mismatch: {name}")
    for name, expected in release["models"].items():
        if hash_file(Path(profile[name]["weights"])) != expected:
            raise ValueError("Frozen provider mismatch")
    if hash_file(Path(profile["entity_semantics_ontology"])) != release["ontology_sha256"]:
        raise ValueError("Frozen ontology mismatch")
    return profile


class WorkerHost:
    def __init__(self, gateway, profile, runtime, worker=camera_main):
        self.gateway, self.profile, self.runtime, self.worker = gateway, profile, runtime, worker
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, name="field-worker-host")
        self.process = self.pipe = self.session = None
        self.ready = False
        self.requested = False
        self.active = None
        self.started = self.dispatched = 0.0
        self.failed_session = None

    def status(self, value):
        with self.gateway.lock:
            self.gateway.worker_status = value

    def start(self):
        self.status("WAITING_FOR_SESSION")
        self.thread.start()

    def shutdown_child(self):
        if self.session is not None:
            self.session.end_inference()
        if self.process is not None:
            if self.process.is_alive() and self.requested:
                try:
                    self.pipe.send(None)
                except (BrokenPipeError, OSError):
                    pass
                self.process.join(1)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(2)
            if self.process.is_alive():
                self.process.kill()
                self.process.join(2)
            self.pipe.close()
            self.process.close()
        self.process = self.pipe = self.session = None
        self.ready = False
        self.requested = False
        self.active = None

    def tick(self):
        with self.gateway.lock:
            session = self.gateway.session
            if session and session.expire_if_idle(perf_counter_ns()):
                self.gateway.pending.take()
            if session and session.closed:
                session = None
        if session is not self.session:
            self.shutdown_child()
            if session is None:
                self.status("WAITING_FOR_SESSION")
                return
            if session.session_id == self.failed_session:
                return
            self.session = session
            if psutil.virtual_memory().available < 2 * 1024**3:
                raise RuntimeError("RAM_RESERVE")
            context = multiprocessing.get_context("spawn")
            self.pipe, child = context.Pipe()
            self.process = context.Process(
                target=self.worker,
                args=(
                    child,
                    session.session_id,
                    session.start.width,
                    session.start.height,
                    self.profile,
                    self.runtime,
                ),
            )
            self.process.start()
            child.close()
            self.started = monotonic()
            self.status("INITIALIZING")
        if self.process is None:
            return
        if not self.process.is_alive():
            raise RuntimeError("WORKER_EXITED")
        if psutil.virtual_memory().available < 2 * 1024**3:
            raise RuntimeError("RAM_RESERVE")
        if not self.ready and monotonic() - self.started > 60:
            raise RuntimeError("STARTUP_TIMEOUT")
        if self.active is not None and monotonic() - self.dispatched > 3:
            raise RuntimeError("INFERENCE_TIMEOUT")
        if self.pipe.poll():
            reply = self.pipe.recv()
            kind = reply[0]
            if kind == "READY" and self.active is None:
                self.ready = True
                self.status("READY")
            elif kind == "REQUEST" and self.ready and not self.requested:
                self.requested = True
            elif kind == "FAILED":
                raise RuntimeError("WORKER_ERROR_" + reply[1])
            elif self.active is None or reply[1] != self.active[0]:
                raise RuntimeError("WRONG_WORKER_IDENTITY")
            else:
                if kind == "RESULT":
                    if reply[2] != self.active[1]:
                        raise RuntimeError("WRONG_WORKER_CAPTURE")
                    now = perf_counter_ns()
                    if not session.closed and 0 <= now - reply[2] < 500_000_000:
                        session.publish_result(
                            session_id=session.session_id,
                            sequence=reply[1],
                            capture_host_ns=reply[2],
                            scene=reply[3],
                            now_ns=now,
                        )
                elif kind in ("EXPIRED", "INVALID_IMAGE", "RESULT_TOO_LARGE"):
                    session.record(kind, perf_counter_ns(), {"sequence": reply[1]})
                else:
                    raise RuntimeError("UNKNOWN_WORKER_REPLY")
                session.end_inference()
                self.active = None
        if self.requested and self.active is None:
            with self.gateway.lock:
                if self.gateway.session is not session or session.closed:
                    return
                packet = self.gateway.pending.take()
                if packet and packet[0] == session.session_id:
                    session.begin_inference(packet[1].sequence, packet[3])
            if packet:
                ident, header, jpeg, captured = packet
                if ident != session.session_id:
                    return
                self.active = header.sequence, captured
                self.requested = False
                self.dispatched = monotonic()
                self.pipe.send((header.model_dump(), jpeg, captured))

    def run(self):
        try:
            while not self.stop.wait(0.01):
                try:
                    self.tick()
                except (RuntimeError, ValueError, OSError, EOFError) as error:
                    self.failed_session = self.session.session_id if self.session else None
                    self.shutdown_child()
                    self.status(
                        "UNAVAILABLE_"
                        + (str(error) if type(error) is RuntimeError else type(error).__name__)
                    )
        finally:
            self.shutdown_child()

    def close(self):
        self.stop.set()
        self.thread.join(10)
        if self.thread.is_alive():
            raise RuntimeError("Field host failed to close")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--cert", type=Path)
    parser.add_argument("--key", type=Path)
    for name in ("ort-runtime", "cuda-libraries", "cudnn-directory"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    token = secrets.token_urlsafe(32)
    gateway = Gateway(token, hash_file(args.manifest))
    runtime = [
        p.resolve(strict=True)
        for p in (args.ort_runtime, args.cuda_libraries, args.cudnn_directory)
    ]
    host = WorkerHost(gateway, release_profile(args.manifest), runtime)
    tls = None
    if args.key or args.cert:
        if not args.key or not args.cert:
            parser.error("Both --cert and --key are required for TLS")
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(args.cert, args.key)
    with FieldHTTPServer((args.host, args.port), gateway, tls) as server:
        print(
            f"Local gateway port {server.server_port}. Ephemeral pairing token: {token}", flush=True
        )
        host.start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            host.close()


if __name__ == "__main__":
    main()
