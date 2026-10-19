"""Explicit acquisition only; never imported or invoked by inference."""

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("configs/depth-checkpoints.json"))
    parser.add_argument("--output", type=Path, default=Path("benchmark-results/task008/models"))
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    for checkpoint in manifest["checkpoints"]:
        repository = checkpoint["repository"]
        if repository not in {
            "depth-anything/Depth-Anything-V2-Small-hf",
            "depth-anything/Depth-Anything-V2-Metric-Outdoor-Small-hf",
        }:
            raise ValueError("Unapproved acquisition repository")
        directory = args.output / repository.split("/")[1]
        directory.mkdir(parents=True, exist_ok=True)
        for filename, artifact in checkpoint["artifacts"].items():
            if filename not in {
                "README.md",
                "config.json",
                "preprocessor_config.json",
                "model.safetensors",
            }:
                raise ValueError("Unexpected artifact name")
            target = directory / filename
            if target.exists():
                with target.open("rb") as stream:
                    if hashlib.file_digest(stream, "sha256").hexdigest() == artifact["sha256"]:
                        continue
                raise ValueError("Existing artifact hash mismatch; preserve and inspect it")
            url = f"https://huggingface.co/{repository}/resolve/{checkpoint['revision']}/{filename}"
            if url != artifact["url"]:
                raise ValueError("Artifact URL disagrees with pinned provenance")
            temporary = target.with_suffix(target.suffix + ".partial")
            if temporary.exists():
                raise ValueError("Partial download exists; inspect it before retrying")
            try:
                with (
                    urllib.request.urlopen(url, timeout=120) as response,
                    temporary.open("xb") as stream,
                ):
                    count = 0
                    while chunk := response.read(1024 * 1024):
                        count += len(chunk)
                        if count > artifact["bytes"]:
                            raise ValueError("Artifact exceeds expected size")
                        stream.write(chunk)
                with temporary.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                if digest != artifact["sha256"] or count != artifact["bytes"]:
                    raise ValueError("Downloaded artifact integrity mismatch")
                temporary.replace(target)
            finally:
                if temporary.exists():
                    temporary.unlink()
        (directory / "sentinel-manifest.json").write_text(json.dumps(checkpoint, indent=2))
        print(repository, "verified")


if __name__ == "__main__":
    main()
