"""Sequential semantic qualification and residual screening; one GPU model at a time."""

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path
from time import sleep

import psutil
from alpha_candidate_isolate import supervise


def gpu_state():
    result = subprocess.run(
        [
            "C:/Windows/System32/nvidia-smi.exe",
            "--query-gpu=name,memory.total,memory.free,driver_version",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    name, total, free, driver = result.stdout.strip().splitlines()[0].split(", ")
    return {"name": name, "total_mib": int(total), "free_mib": int(free), "driver": driver}


def save(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    state = {
        "status": "RUNNING",
        "release_qualified": False,
        "steps": [],
        "hardware": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "logical_cores": psutil.cpu_count(),
            "physical_cores": psutil.cpu_count(logical=False),
            "ram_bytes": psutil.virtual_memory().total,
            "free_ram_bytes": psutil.virtual_memory().available,
            "gpu": gpu_state(),
        },
    }
    path = output / "batch-status.json"
    save(path, state)

    def step(name, command, seconds, optional=False):
        before = gpu_state()
        if before["free_mib"] < 1024:
            raise RuntimeError("GPU headroom below 1 GiB")
        record = {"name": name, "status": "RUNNING", "optional": optional, "gpu_before": before}
        state["steps"].append(record)
        save(path, state)
        print(f"START {name}; hard cap {seconds}s", flush=True)
        report = supervise(command, output / (name + "-process"), seconds)
        record.update(report)
        # Observe actual post-exit recovery, without assuming no other GPU users exist.
        for _ in range(10):
            after = gpu_state()
            if after["free_mib"] >= before["free_mib"] - 128:
                break
            sleep(1)
        record["gpu_after"] = after
        record["gpu_returned_near_observed_baseline"] = (
            after["free_mib"] >= before["free_mib"] - 128
        )
        save(path, state)
        print(f"END {name}: {report['status']}", flush=True)
        if report["status"] != "EXITED_SUCCESS" and not optional:
            raise RuntimeError("Required batch step failed: " + name)
        return report["status"] == "EXITED_SUCCESS"

    python = sys.executable
    runtime = root / "benchmark-results/v0-rescue"
    common = [
        "--seconds",
        "600",
        "--device",
        "cuda:0",
        "--ort-runtime",
        str(runtime / "gpu-runtime"),
        "--cuda-libraries",
        str(runtime / "gpu-libraries"),
        "--cudnn-directory",
        str(runtime / "cudnn-9.10/nvidia/cudnn/bin"),
    ]
    try:
        for arm in ("A", "B"):
            step(
                "presentation-" + arm,
                [
                    python,
                    str(root / "tools/alpha_continuous_replay.py"),
                    "--arm",
                    arm,
                    "--output",
                    str(output / ("presentation-" + arm)),
                    *common,
                ],
                2700,
            )
        step(
            "pair-comparison",
            [
                python,
                str(root / "tools/alpha_compare_continuous.py"),
                "--a",
                str(output / "presentation-A"),
                "--b",
                str(output / "presentation-B"),
                "--output",
                str(output / "paired-result.json"),
            ],
            300,
        )
        residual = output / "FINAL_RESIDUAL_SEMANTIC_TARGETS.json"
        step(
            "residual-extraction",
            [
                python,
                str(root / "tools/alpha_residuals.py"),
                "--run",
                str(output / "presentation-B"),
                "--output",
                str(residual),
            ],
            300,
        )
        population = json.loads(residual.read_text())
        if any(target["screenable"] for target in population["targets"]):
            config = json.loads((output / "presentation-B/configuration.json").read_text())
            for model in ("yoloe-11s-prompt-free", "yolov8s-worldv2", "grounding-dino"):
                step(
                    model,
                    [
                        python,
                        str(root / "tools/alpha_candidate_isolate.py"),
                        "--model",
                        model,
                        "--video",
                        config["input"],
                        "--residual",
                        str(residual),
                        "--torch-runtime",
                        str(root / "benchmark-results/v02/torch-gpu-runtime"),
                        "--output",
                        str(output / model),
                        "--minutes",
                        "5",
                    ],
                    330,
                    optional=True,
                )
        else:
            state["candidate_screening"] = "NO_SCREENABLE_RESIDUALS"
        step(
            "roll-canvas-probe",
            [
                python,
                str(root / "tools/alpha_roll_probe.py"),
                "--config",
                str(output / "presentation-B/configuration.json"),
                "--output",
                str(output / "roll-canvas-probe.json"),
            ],
            180,
        )
        state["status"] = "SEMANTIC_BATCH_COMPLETE_REQUIRES_RESULT_REVIEW"
    except BaseException as error:
        state.update(status="INCOMPLETE", error_type=type(error).__name__)
        raise
    finally:
        save(path, state)


if __name__ == "__main__":
    main()
