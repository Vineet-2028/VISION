"""Explicit pinned teacher setup; no executable checkpoint or repository code."""

import argparse
import hashlib
import json
import math
import os
import shutil
from pathlib import Path


def verify(path, record):
    if path.stat().st_size != record["bytes"]:
        raise ValueError(f"Teacher size mismatch: {record['name']}")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if "sha256" in record:
        if digest != record["sha256"]:
            raise ValueError("Teacher SHA256 mismatch")
    else:
        data = path.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if blob != record["git_blob_sha1"]:
            raise ValueError("Teacher metadata git object mismatch")
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("configs/perception/offline-teacher-v1.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmark-results/v02/models/grounding-dino-base"),
    )
    args = parser.parse_args()
    record = json.loads(args.registry.read_text())
    if record["repository"] != "IDEA-Research/grounding-dino-base" or record["schema_version"] != 1:
        raise ValueError("Unapproved teacher repository")
    args.output.mkdir(parents=True, exist_ok=True)
    size = sum(item["bytes"] for item in record["files"])
    budget_gb = float(os.environ.get("VISION_DATA_BUDGET_GB", "3"))
    if not math.isfinite(budget_gb) or budget_gb <= 0:
        raise ValueError("Invalid VISION_DATA_BUDGET_GB")
    free = shutil.disk_usage(args.output).free
    # Reserve room for the final assets plus download staging. No dataset download.
    if size * 2 > min(budget_gb * 1024**3, free * 0.1):
        raise ValueError("Teacher acquisition exceeds configured budget/free-disk guardrail")
    for item in record["files"]:
        if Path(item["name"]).name != item["name"]:
            raise ValueError("Unsafe teacher asset path")
        target = args.output / item["name"]
        if target.exists():
            verify(target, item)  # Never replace a corrupt existing asset silently.
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["HF_HUB_DISABLE_XET"] = "1"
    from huggingface_hub import hf_hub_download

    hashes = {}
    for item in record["files"]:
        target = args.output / item["name"]
        if not target.exists():
            hf_hub_download(
                record["repository"],
                item["name"],
                revision=record["revision"],
                local_dir=args.output,
                token=False,
            )
        hashes[item["name"]] = verify(target, item)
        print(f"VERIFIED {item['name']}", flush=True)
    manifest = {
        "repository": record["repository"],
        "revision": record["revision"],
        "hashes": hashes,
        "bytes": size,
        "free_disk_before": free,
        "configured_budget_gb": budget_gb,
        "status": "ASSETS_VERIFIED_NOT_QUALIFIED",
    }
    output = args.output / "acquisition.json"
    if not output.exists():
        with output.open("x") as stream:
            json.dump(manifest, stream, indent=2)


if __name__ == "__main__":
    main()
