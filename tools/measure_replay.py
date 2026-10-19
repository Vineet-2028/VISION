"""Measure an existing headless replay configuration in an isolated child process."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import psutil

from perception_lab.detector_runtime import file_hash


def measure(config, output, timeout):
    if output.exists() or output.with_suffix(".log").exists():
        raise ValueError("Output exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    samples = 0
    first = last = peak = 0
    started = time.monotonic()
    with output.with_suffix(".log").open("x", encoding="utf-8") as stream:
        child = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "perception_lab.cli",
                "replay",
                "--headless",
                "--config",
                str(config),
            ],
            stdout=stream,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        process = psutil.Process(child.pid)
        try:
            while child.poll() is None:
                if time.monotonic() - started > timeout:
                    raise TimeoutError("Replay exceeded explicit wall-time limit")
                try:
                    rss = sum(
                        p.memory_info().rss for p in [process, *process.children(recursive=True)]
                    )
                    first = rss if samples == 0 else first
                    last, peak = rss, max(peak, rss)
                    samples += 1
                except psutil.NoSuchProcess:
                    pass
                time.sleep(1)
        finally:
            if child.poll() is None:
                for descendant in process.children(recursive=True):
                    descendant.kill()
                child.kill()
            child.wait()
    text = output.with_suffix(".log").read_text(encoding="utf-8")
    report = {
        "schema_version": 1,
        "status": "MEASURED_LOCALLY" if child.returncode == 0 else "FAILED",
        "configuration_file_sha256": file_hash(config),
        "wall_seconds": time.monotonic() - started,
        "memory": {
            "start_rss": first,
            "peak_sampled_rss": peak,
            "end_sampled_rss": last,
            "samples": samples,
            "interval_seconds": 1,
            "scope": "child process tree; includes JVM; sampled peak",
        },
    }
    if child.returncode == 0:
        report["replay"] = json.loads(text)
        replay = report["replay"]
        if replay["frame_counts"]["processed"] == 0 or replay["timing"]["component"]["count"] == 0:
            report["status"] = "FAILED_NO_COMPONENT_OUTPUT"
        config_values = json.loads(config.read_text(encoding="utf-8"))
        if config_values.get("motion") is not None and replay.get("flow_pairs_published", 0) == 0:
            # The first flow call only primes its previous-frame buffer. A processed
            # frame/component invocation does not establish a measured motion pair.
            report["status"] = "FAILED_NO_FLOW_PAIRS"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if child.returncode != 0:
        raise RuntimeError("Replay failed; inspect private log")
    if report["status"] != "MEASURED_LOCALLY":
        raise RuntimeError("Replay produced no component results; inspect report")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=1800)
    args = parser.parse_args()
    measure(args.config, args.output, args.timeout)
