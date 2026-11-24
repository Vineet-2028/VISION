"""Explicit setup-only download of official pinned research assets, never runtime."""

import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry", type=Path, default=Path("configs/perception/research-models-v02.json")
    )
    parser.add_argument("--output", type=Path, default=Path("benchmark-results/v02/models"))
    args = parser.parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    if registry["schema_version"] != 1:
        raise ValueError("Unsupported registry")
    args.output.mkdir(parents=True, exist_ok=True)
    for model in registry["models"]:
        name, url, expected = model["filename"], model["url"], model["sha256"]
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+\.pt", name) or not re.fullmatch(
            r"[a-f0-9]{64}", expected
        ):
            raise ValueError("Invalid pinned asset")
        if not url.startswith("https://github.com/ultralytics/assets/releases/download/v8.4.0/"):
            raise ValueError("Unapproved model source")
        target = args.output / name
        if target.exists():
            with target.open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                    raise ValueError("Existing model hash mismatch; refusing replacement")
            print(f"VERIFIED {model['id']}", flush=True)
            continue
        temporary = args.output / (name + ".part")
        digest = hashlib.sha256()
        length = 0
        with urllib.request.urlopen(url, timeout=60) as response:
            final = urlparse(response.url)
            if final.scheme != "https" or final.hostname not in {
                "github.com",
                "release-assets.githubusercontent.com",
            }:
                raise ValueError("Unexpected asset redirect")
            with temporary.open("xb") as sink:
                while chunk := response.read(1024 * 1024):
                    length += len(chunk)
                    if length > model["bytes"] or length > 500_000_000:
                        raise ValueError("Asset exceeds registered size")
                    digest.update(chunk)
                    sink.write(chunk)
        if length != model["bytes"] or digest.hexdigest() != expected:
            raise ValueError("Downloaded model size/hash mismatch; not activated")
        # A concurrent setup must never overwrite a different target.
        target.hardlink_to(temporary)
        temporary.unlink()
        print(f"ACQUIRED {model['id']} sha256={expected}", flush=True)


if __name__ == "__main__":
    main()
