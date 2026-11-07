"""Build an offline reviewed manifest. No media upload, training or policy promotion."""

import argparse
import json
import time
from pathlib import Path

from perception_lab.product_data import (
    Artifact,
    ConsentGrant,
    DatasetRegistry,
    LocalObjectStore,
    Review,
    hard_cases,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Explicit local JSON: artifacts, reviews, grants")
    parser.add_argument(
        "output",
        type=Path,
        help="New output path; existing versions cannot be overwritten",
    )
    parser.add_argument(
        "--registry", type=Path, required=True, help="Persistent consent/version ledger"
    )
    parser.add_argument(
        "--objects", type=Path, required=True, help="Private local object directory"
    )
    args = parser.parse_args()
    if args.input.stat().st_size > 4_000_000:
        parser.error("Input exceeds local review budget")
    data = json.loads(args.input.read_text(encoding="utf-8"))
    artifacts = [Artifact.model_validate(x) for x in data["artifacts"]]
    reviews = [Review.model_validate(x) for x in data["reviews"]]
    grants = [ConsentGrant.model_validate(x) for x in data["grants"]]
    registry = DatasetRegistry(args.registry, LocalObjectStore(args.objects))
    try:
        version = registry.publish(artifacts, reviews, grants, int(time.time()))
        result = registry.manifest(version)
    finally:
        registry.close()
    result["review_queue"] = hard_cases(artifacts, reviews)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2)
    print("Reviewed manifest saved. No training or production promotion performed.")


if __name__ == "__main__":
    main()
