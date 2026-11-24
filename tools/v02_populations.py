"""Freeze complete rescued alert and canonical reference populations, not results."""

import argparse
import hashlib
import json
from pathlib import Path

from v0_analyze import references


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def populations(run, reference_path, *, alert_count=60, event_count=188):
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "COMPLETE":
        raise ValueError("Rescued run must be complete")
    frames, events = references(reference_path)
    relevant = {key: value for key, value in events.items() if value["relevant"]}
    if len(relevant) != event_count:
        raise ValueError("Canonical event denominator changed")
    observations = {key: [] for key in relevant}
    for frame in frames:
        for annotation in frame["annotations"]:
            key = f"{frame['clip_id']}:{annotation['ground_truth_track_id']}"
            if key in observations:
                observations[key].append(
                    {
                        "observation_ns": frame["observation_ns"],
                        "width": frame["width"],
                        "height": frame["height"],
                        "reference_box": annotation["box"],
                        "reference_label": annotation["label"],
                    }
                )
    alerts = []
    seen = set()
    trace = run / "updates.jsonl"
    trace_hash = hashlib.sha256()
    with trace.open("rb") as stream:
        for line in stream:
            trace_hash.update(line)
            row = json.loads(line)
            for output in (row.get("alert_output_set") or {}).get("outputs", []):
                if not output["delivered"]:
                    continue
                intent = output["intent"]
                identifier = intent["alert_id"]
                if identifier in seen:
                    raise ValueError("Duplicate accepted alert identity")
                seen.add(identifier)
                if output["presentation"]["speech_text"] != "Object.":
                    raise ValueError("Rescued generic population changed")
                entity = next(
                    (
                        e
                        for e in (row.get("world") or {}).get("entities", [])
                        if e["entity_id"] == intent["entity_id"]
                    ),
                    None,
                )
                alerts.append(
                    {
                        "alert_id": identifier,
                        "event_id": intent["event_id"],
                        "source_observation_ns": intent["source_observation_ns"],
                        "publication_frame": row["identity"],
                        "entity_id": intent["entity_id"],
                        "track_id": entity["source_track_id"] if entity else None,
                        "entity_observed_ns": (
                            row["identity"]["observation_ns"] - entity["observation_age_ns"]
                            if entity
                            else None
                        ),
                        "entity_box": entity["box"] if entity else None,
                        "entity_observation_status": entity["observation_status"]
                        if entity
                        else None,
                        "entity_box_basis": "PUBLICATION_WORLD_STATE_MAY_BE_PREDICTED",
                        "rescued_text": output["presentation"]["speech_text"],
                    }
                )
    if len(alerts) != alert_count:
        raise ValueError("Accepted alert denominator changed")
    return {
        "schema_version": 1,
        "status": "POPULATION_FROZEN_NOT_MODEL_EVALUATION",
        "reference_status": "PROTOTYPE_REFERENCE_NOT_INDEPENDENT_HUMAN_TRUTH",
        "teacher_output_status": "MODEL_PSEUDO_LABEL",
        "source_sha256": manifest["source_sha256"],
        "run_manifest_sha256": file_hash(run / "manifest.json"),
        "updates_sha256": trace_hash.hexdigest(),
        "references_sha256": file_hash(reference_path),
        "alert_denominator": alert_count,
        "event_denominator": event_count,
        "alerts": alerts,
        "events": [
            {"event_id": key, "observations": observations[key]} for key in sorted(relevant)
        ],
        "limitations": [
            "Publication frame may be later than source evidence; do not silently substitute it",
            "World boxes may be predicted; do not treat them as original observed annotations",
            "All reference observations retained; no successful-frame selection",
            "No candidate recovery, accuracy, trackability or runtime measurement yet",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = populations(args.run, args.references)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(
        json.dumps(
            {key: result[key] for key in ("status", "alert_denominator", "event_denominator")}
        )
    )


if __name__ == "__main__":
    main()
