"""Real subprocesses verify that a stalled optional candidate cannot hold the parent."""

import importlib
import json
import sys
from pathlib import Path

import psutil
import pytest


@pytest.fixture
def isolate(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    return importlib.import_module("alpha_candidate_isolate")


def test_hard_deadline_terminates_child_and_persists_failed_artifact(isolate, tmp_path):
    output = tmp_path / "hung"
    report = isolate.supervise(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        output,
        0.3,
        reserve_bytes=0,
        interval=0.02,
    )
    assert report["status"] == "HARD_WALL_TIMEOUT"
    assert report["child_exit_code"] is not None
    assert report["elapsed_seconds"] < 10
    assert json.loads((output / "process-summary.json").read_text()) == report
    assert not (output / "process-summary.tmp").exists()


def test_failed_child_never_becomes_success_and_ram_gate_prevents_launch(isolate, tmp_path):
    command = [sys.executable, "-c", "raise SystemExit(7)"]
    failed = isolate.supervise(command, tmp_path / "failed", 10, reserve_bytes=0)
    assert failed["status"] == "CHILD_FAILED" and failed["child_exit_code"] == 7
    gated = isolate.supervise(
        command, tmp_path / "gated", 10, reserve_bytes=psutil.virtual_memory().total + 1
    )
    assert gated["status"] == "FREE_RAM_RESERVE_REACHED_BEFORE_START"
    assert gated["child_exit_code"] is None


def test_exited_launcher_cannot_leave_observed_descendant_running(isolate, tmp_path):
    pid_file = tmp_path / "descendant.pid"
    script = (
        "import subprocess, sys, time; from pathlib import Path; "
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
        f"Path({str(pid_file)!r}).write_text(str(child.pid)); time.sleep(1)"
    )
    try:
        report = isolate.supervise(
            [sys.executable, "-c", script],
            tmp_path / "exited-launcher",
            10,
            reserve_bytes=0,
            interval=0.02,
        )
        assert report["status"] == "EXITED_SUCCESS"
        assert pid_file.exists()
        assert not psutil.pid_exists(int(pid_file.read_text()))
    finally:
        # A regression must not leave the test's own sleeping process behind.
        if pid_file.exists():
            try:
                child = psutil.Process(int(pid_file.read_text()))
                child.kill()
                child.wait(timeout=5)
            except psutil.NoSuchProcess:
                pass


def test_low_device_memory_prevents_gpu_child_launch(isolate, tmp_path, monkeypatch):
    monkeypatch.setattr(isolate, "gpu_free_mib", lambda _: 1023)
    report = isolate.supervise(
        [sys.executable, "-c", "raise RuntimeError('must not run')"],
        tmp_path / "vram",
        10,
        reserve_bytes=0,
        gpu_probe="test-probe",
    )
    assert report["status"] == "FREE_VRAM_RESERVE_REACHED_BEFORE_START"
    assert report["minimum_sampled_device_free_mib"] == 1023
    assert report["child_exit_code"] is None


def test_cleanup_failure_still_persists_failed_summary(isolate, monkeypatch, tmp_path):
    def fail_cleanup(*_):
        raise RuntimeError("test-only private detail")

    monkeypatch.setattr(isolate, "terminate_owned", fail_cleanup)
    output = tmp_path / "cleanup-failed"
    with pytest.raises(RuntimeError, match="Owned process cleanup failed"):
        isolate.supervise([sys.executable, "-c", "pass"], output, 10, reserve_bytes=0)
    report = json.loads((output / "process-summary.json").read_text())
    assert report["status"] == "OWNED_PROCESS_CLEANUP_FAILED"
    assert report["cleanup_error_type"] == "RuntimeError"
    assert "private detail" not in json.dumps(report)
