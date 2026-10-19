"""Explicit COCO-2017 subset acquisition; opt-in/manual workflow only, never normal CI.

Run with the lab Python, after downloading the official annotation archive. This
retains source/license URLs. Human review is still required before redistribution.
"""

import argparse
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("datasets/raw/coco2017"))
    parser.add_argument("--per-class", type=int, default=6)
    args = parser.parse_args()
    if not 1 <= args.per_class <= 100:
        parser.error("per-class must be 1..100")
    archive = args.root / "annotations_trainval2017.zip"
    with zipfile.ZipFile(archive) as zipped:
        raw = zipped.read("annotations/instances_val2017.json")
    source = json.loads(raw)
    licenses = {item["id"]: item for item in source["licenses"]}
    # License IDs are validated by names, rather than trusting an undocumented numeric mapping.
    allowed = {
        key
        for key, item in licenses.items()
        if item["name"] in {"Attribution License", "Attribution-ShareAlike License"}
    }
    if not allowed:
        raise ValueError("COCO license metadata changed; review required")
    images = {item["id"]: item for item in source["images"] if item["license"] in allowed}
    categories = {
        1: "PERSON",
        2: "BICYCLE",
        3: "CAR",
        4: "MOTORCYCLE",
        6: "BUS",
        7: "TRAIN",
        8: "TRUCK",
        18: "DOG",
    }
    annotations = {}
    for item in source["annotations"]:
        if item["category_id"] in categories and item["image_id"] in images:
            annotations.setdefault(item["image_id"], []).append(item)
    selected = set()
    selection = {}
    for category, name in categories.items():
        eligible = sorted(
            image_id
            for image_id, items in annotations.items()
            if any(a["category_id"] == category and not a["iscrowd"] for a in items)
        )
        # Fixed sorted IDs, first K per priority class. Biased diagnostic subset, not random sample.
        selection[name] = eligible[: args.per_class]
        selected.update(selection[name])
    entries = []
    destination = args.root / "images"
    destination.mkdir(parents=True, exist_ok=True)
    for image_id in sorted(selected):
        item = images[image_id]
        filename = f"{image_id:012d}.jpg"
        url = f"https://s3.amazonaws.com/images.cocodataset.org/val2017/{filename}"
        target = destination / filename
        if not target.exists():
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read(20_000_001)
            if len(data) > 20_000_000:
                raise ValueError("Unexpected image size")
            target.write_bytes(data)
        entries.append(
            {
                "image_id": image_id,
                "path": f"images/{filename}",
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "width": item["width"],
                "height": item["height"],
                "source_url": url,
                "attribution_url": item["flickr_url"],
                "license": licenses[item["license"]],
                "scenario": "UNKNOWN",
                "lighting": "UNKNOWN",
                "blur": "UNKNOWN",
                "annotations": [
                    {
                        "id": a["id"],
                        "label": categories[a["category_id"]],
                        "box": [
                            a["bbox"][0],
                            a["bbox"][1],
                            a["bbox"][0] + a["bbox"][2],
                            a["bbox"][1] + a["bbox"][3],
                        ],
                        "crowd": bool(a["iscrowd"]),
                        "ignore": False,
                        "occluded": None,
                        "truncated": None,
                        "difficulty": "UNKNOWN",
                    }
                    for a in annotations[image_id]
                ],
            }
        )
        print(f"COCO validation image {image_id} acquired")
    manifest = {
        "schema_version": 1,
        "dataset": "COCO-2017-val-Sentinel-P0-diagnostic-v1",
        "annotation_sha256": hashlib.sha256(raw).hexdigest(),
        "selection": selection,
        "selection_policy": "first sorted licensed IDs per P0 class",
        "scope": "P0 classes only; all P0 annotations retained, including crowd",
        "limitations": (
            "Small biased still-image subset; not a walking-video or safety validation set"
        ),
        "images": entries,
    }
    output = args.root / "sentinel-subset.json"
    encoded = json.dumps(manifest, sort_keys=True, indent=2).encode()
    if output.exists() and output.read_bytes() != encoded:
        raise ValueError("Existing manifest differs; choose a new dataset directory/version")
    output.write_bytes(encoded)
    print(f"Dataset: {len(entries)} images, SHA256 {hashlib.sha256(encoded).hexdigest()}")


if __name__ == "__main__":
    main()
