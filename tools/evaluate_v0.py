"""Run frozen V0 evaluation sequentially, with immutable new output directories."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def freeze(output, config):
    files = [
        *ROOT.glob("apps/perception-lab/src/**/*.py"),
        *ROOT.glob("packages/guardian-core/src/main/**/*.java"),
        *ROOT.glob("tools/v0_*.py"),
        Path(__file__),
        ROOT / "package-lock.json",
    ]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    inventory = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=json"],
        check=True,
        capture_output=True,
        text=True,
    )
    (output / "software-freeze.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "files_sha256": hashes,
                "python_packages": json.loads(inventory.stdout),
                "input_configuration_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
                "note": "Includes dirty/untracked sources; not a clean Git revision",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--references",
        type=Path,
        default=ROOT / "datasets/tracking_v1/sentinel-track-review-prototype.json",
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    freeze(args.output, args.config)

    def execute(tool, *arguments):
        subprocess.run(
            [sys.executable, str(ROOT / "tools" / tool), *map(str, arguments)], check=True
        )

    config = json.loads(args.config.read_text(encoding="utf-8"))
    source = args.config.resolve().parent / config["input"]
    review = args.output / "blind-review"
    execute("v0_review.py", "--source", source, "--packet", review)
    for name, mode in (("realtime", "REALTIME"), ("offline", "OFFLINE_REPLAY")):
        directory = args.output / name
        execute("v0_replay.py", "--config", args.config, "--output", directory, "--mode", mode)
        execute(
            "v0_analyze.py",
            "--run",
            directory,
            "--references",
            args.references,
            "--review",
            review / "manifest.json",
            "--existing-review",
            ROOT / "docs/research/results/task017-review-packet-2026-10-25.json",
        )
    execute("v0_ablation.py", "--config", args.config, "--output", args.output / "ablation")
    execute("v0_reasoning.py", "--config", args.config, "--output", args.output / "reasoning")
    from v0_review import examples

    examples(source, args.output / "offline/analysis.json", args.output / "examples")
    print("V0 measurements complete. Human review and engineering interpretation remain explicit.")


if __name__ == "__main__":
    main()
