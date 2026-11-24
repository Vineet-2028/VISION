"""Export completed replay evidence for a local demo; never label it safety validated."""

import argparse
import json
from pathlib import Path


def export(directory, output):
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest["status"] != "COMPLETE":
        raise ValueError("Cannot export an incomplete replay as a demo")
    output.mkdir(parents=True, exist_ok=False)
    count = 0
    with (
        (directory / "updates.jsonl").open(encoding="utf-8") as source,
        (output / "frames.jsonl").open("x", encoding="utf-8") as target,
    ):
        for line in source:
            row = json.loads(line)
            packet = {
                "schema_version": 1,
                "mode": row["mode"],
                "frame": row["identity"],
                "dimensions": {"width": row["width"], "height": row["height"]},
                "source_to_publication_age_ns": row["source_to_publication_age_ns"],
                "detector": row.get("detector"),
                "tracks": row.get("tracks"),
                "world": row.get("world"),
                "corridor": row.get("corridor_analysis"),
                "trajectory": row.get("trajectory_set"),
                "interaction": row.get("interaction_analysis"),
                "risk": row.get("risk_assessment_set"),
                "attention": row.get("attention_decision_set"),
                "alerts": row.get("alert_output_set"),
                "provider_state": row.get("provider_state"),
                "errors": row.get("errors", []),
                "warnings": row.get("warnings", []),
                "physical_accuracy_validated": False,
                "production_safety_validated": False,
            }
            target.write(json.dumps(packet, allow_nan=False, separators=(",", ":")) + "\n")
            count += 1
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_sha256": manifest["source_sha256"],
                "configuration_sha256": manifest["configuration_sha256"],
                "mode": manifest["mode"],
                "updates": count,
                "physical_accuracy_validated": False,
                "production_safety_validated": False,
                "offline_age_policy": "null is unavailable, never zero realtime age",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    export(args.run, args.output)
