"""Spawn an independent worker to verify gateway handoff and shutdown pressure."""

import importlib
from pathlib import Path
from time import monotonic, perf_counter_ns, sleep

import pytest

from perception_lab.field_protocol import PROTOCOL, FrameHeader, SessionStart
from perception_lab.field_state import FieldSession


def worker_fixture(pipe, session_id, width, height, profile, runtime):
    try:
        pipe.send(("READY",))
        while True:
            pipe.send(("REQUEST",))
            packet = pipe.recv()
            if packet is None:
                return
            header, _, captured = packet
            pipe.send(("RESULT", header["sequence"], captured, {"test_value": "fixture"}))
    finally:
        pipe.close()


def test_host_publishes_matching_worker_result_and_reclaims_child(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    module = importlib.import_module("alpha_field_gateway")

    class Ram:
        available = 4 * 1024**3

    monkeypatch.setattr(module.psutil, "virtual_memory", lambda: Ram())
    gateway = module.Gateway("x" * 32, "test")
    session = FieldSession(
        SessionStart(
            protocol_version=PROTOCOL,
            client_version="test",
            device_id="fixture",
            mode="DESKTOP_REALTIME",
            width=320,
            height=240,
            format="JPEG",
            capabilities=["NO_AUDIO"],
        ),
        "test",
        perf_counter_ns(),
    )
    gateway.session = session
    host = module.WorkerHost(gateway, {}, [], worker_fixture)
    host.start()
    try:
        until = monotonic() + 8
        while gateway.worker_status != "READY" and monotonic() < until:
            with session.lock:
                session.last_client_ns = perf_counter_ns()
            sleep(0.02)
        assert gateway.worker_status == "READY"
        now = perf_counter_ns()
        c = session.begin_sync(now, now, now)
        session.finish_sync(str(c["challenge"]), now, now)
        header = FrameHeader(
            protocol_version=PROTOCOL,
            session_id=session.session_id,
            sequence=4,
            camera_ns=str(now),
            capture_ns=str(now),
            send_ns=str(now),
            sync_version=1,
            rotation=0,
            width=320,
            height=240,
            format="JPEG",
            jpeg_quality=75,
        )
        captured = session.accept_frame(header, now)
        gateway.pending.put((session.session_id, header, b"fixture", captured))
        until = monotonic() + 1
        received = None
        while received is None and monotonic() < until:
            received = session.snapshot(perf_counter_ns())["result"]
            sleep(0.005)
        assert received is not None and received["sequence"] == 4
        assert received["scene"] == {"test_value": "fixture"}
    finally:
        child = host.process
        host.close()
        assert not host.thread.is_alive()
        if child is not None:
            with pytest.raises(ValueError, match="closed"):
                _ = child.pid
