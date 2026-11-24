"""One research candidate per child process, with parent-enforced resource/time limits."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from time import monotonic, sleep

import psutil


def terminate_owned(process, observed_descendants=()):
    """Kill only this launcher-owned child and its descendants, never other applications."""
    try:
        descendants = (
            psutil.Process(process.pid).children(recursive=True) if process.poll() is None else []
        )
    except psutil.NoSuchProcess:
        descendants = []
    # Retain observed descendants even if their launcher has already exited.
    # psutil Process objects check process identity before signaling a reused PID.
    descendants = list({p: None for p in (*observed_descendants, *descendants)})
    for child in reversed(descendants):
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
    if process.poll() is None:
        process.kill()
    process.wait(timeout=10)
    _, alive = psutil.wait_procs(descendants, timeout=10)
    if alive:
        raise RuntimeError("Owned descendant did not terminate")


def gpu_free_mib(executable):
    measurement = subprocess.check_output(
        [str(executable), "-i", "0", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
        text=True,
        timeout=5,
    )
    return int(measurement.strip())


def supervise(command, output, seconds, *, reserve_bytes=2 * 1024**3, interval=0.5, gpu_probe=None):
    if seconds <= 0 or reserve_bytes < 0 or interval <= 0:
        raise ValueError("Invalid process limits")
    output.mkdir(parents=True, exist_ok=False)
    started = monotonic()
    reason = "NOT_STARTED"
    child = None
    peak_rss = 0
    minimum_gpu_free = None
    last_gpu_sample = started
    observed_descendants = set()
    free_before = psutil.virtual_memory().available
    try:
        if free_before < reserve_bytes:
            reason = "FREE_RAM_RESERVE_REACHED_BEFORE_START"
        elif gpu_probe and (minimum_gpu_free := gpu_free_mib(gpu_probe)) < 1024:
            reason = "FREE_VRAM_RESERVE_REACHED_BEFORE_START"
        else:
            with (output / "child.log").open("x", encoding="utf-8") as log:
                child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
                reason = "RUNNING"
                while child.poll() is None:
                    if monotonic() - started >= seconds:
                        reason = "HARD_WALL_TIMEOUT"
                        break
                    if psutil.virtual_memory().available < reserve_bytes:
                        reason = "FREE_RAM_RESERVE_REACHED"
                        break
                    if gpu_probe and monotonic() - last_gpu_sample >= 5:
                        free_gpu = gpu_free_mib(gpu_probe)
                        minimum_gpu_free = min(minimum_gpu_free, free_gpu)
                        last_gpu_sample = monotonic()
                        if free_gpu < 1024:
                            reason = "FREE_VRAM_RESERVE_REACHED"
                            break
                    try:
                        root = psutil.Process(child.pid)
                        tree = [root, *root.children(recursive=True)]
                        observed_descendants.update(tree[1:])
                        peak_rss = max(peak_rss, sum(p.memory_info().rss for p in tree))
                    except psutil.NoSuchProcess:
                        pass
                    sleep(min(interval, max(0.001, seconds - (monotonic() - started))))
                if reason == "RUNNING":
                    reason = "EXITED_SUCCESS" if child.returncode == 0 else "CHILD_FAILED"
    except BaseException:
        reason = "SUPERVISOR_FAILED_OR_INTERRUPTED"
        raise
    finally:
        cleanup_error = None
        if child is not None:
            try:
                terminate_owned(child, observed_descendants)
            except Exception as error:
                cleanup_error = error
                reason = "OWNED_PROCESS_CLEANUP_FAILED"
        report = {
            "status": reason,
            "child_exit_code": child.returncode if child is not None else None,
            "elapsed_seconds": monotonic() - started,
            "hard_wall_seconds": seconds,
            "reserve_bytes": reserve_bytes,
            "free_ram_before": free_before,
            "free_ram_after": psutil.virtual_memory().available,
            "minimum_sampled_device_free_mib": minimum_gpu_free,
            "device_free_reserve_mib": 1024 if gpu_probe else None,
            "sampled_process_tree_rss_peak": peak_rss,
            "native_hang_containment": "PARENT_TERMINATES_OWNED_PROCESS",
            "cleanup_error_type": type(cleanup_error).__name__ if cleanup_error else None,
        }
        temporary = output / "process-summary.tmp"
        temporary.write_text(json.dumps(report, indent=2), encoding="utf-8")
        temporary.replace(output / "process-summary.json")
        if cleanup_error is not None:
            raise RuntimeError(
                "Owned process cleanup failed; inspect process summary"
            ) from cleanup_error
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        choices=("yoloe-11s-prompt-free", "yolov8s-worldv2", "grounding-dino"),
        required=True,
    )
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--residual", type=Path, required=True)
    parser.add_argument("--torch-runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minutes", type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.minutes <= 10:
        parser.error("Hard budget must be 1..10 minutes")
    command = [sys.executable]
    if args.model == "grounding-dino":
        command += [str(Path(__file__).with_name("v02_teacher_population.py"))]
    else:
        command += [
            str(Path(__file__).with_name("v02_candidate_population.py")),
            "--model",
            args.model,
            "--video",
            str(args.video.resolve()),
        ]
    command += [
        "--residual",
        str(args.residual.resolve()),
        "--torch-runtime",
        str(args.torch_runtime.resolve()),
        "--device",
        "cuda",
        "--warmup",
        "2",
        "--max-run-minutes",
        str(args.minutes),
        "--output",
        str((args.output / "candidate").resolve()),
    ]
    report = supervise(command, args.output, args.minutes * 60)
    print(json.dumps(report))
    if report["status"] != "EXITED_SUCCESS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
