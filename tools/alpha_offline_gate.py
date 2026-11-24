"""Run the canonical 18,000-frame evaluation using a specified source checkout."""

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


def sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def run(args):
    checkout = args.checkout.resolve()
    if args.frozen_manifest:
        hashes = json.loads(args.frozen_manifest.read_text())["source_hashes"]
        for relative, expected in hashes.items():
            path = (checkout / relative).resolve()
            if not path.is_relative_to(checkout) or sha256(path) != expected:
                raise ValueError(f"Frozen source mismatch: {relative}")
    sys.path[:0] = [str(checkout / "tools"), str(checkout / "apps/perception-lab/src")]
    import rescue_runtime
    import v0_replay

    import perception_lab

    for module in (perception_lab, rescue_runtime, v0_replay):
        if not Path(module.__file__).resolve().is_relative_to(checkout):
            raise RuntimeError(f"Wrong checkout for {module.__name__}")
    raw = json.loads(args.config.read_text())
    for key in ("input", "calibration", "entity_semantics_ontology"):
        if raw.get(key):
            raw[key] = str((args.config.parent / raw[key]).resolve(strict=True))
    for key in ("detector", "depth", "segmentation"):
        if (raw.get(key) or {}).get("weights"):
            raw[key]["weights"] = str(
                (args.config.parent / raw[key]["weights"]).resolve(strict=True)
            )
    raw["realtime_rescue"] = False
    config = args.output / "offline-input.json"
    if args.recheck:
        if json.loads(config.read_text()) != raw:
            raise ValueError("Saved offline input differs from requested profile")
    else:
        args.output.mkdir(parents=True, exist_ok=False)
        config.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    jar = checkout / "packages/guardian-core/target/guardian-core-0.1.0.jar"
    provenance = {
        "input_configuration_sha256": sha256(args.config),
        "guardian_jar_sha256": sha256(jar),
        "replay_tool_sha256": sha256(Path(v0_replay.__file__)),
        "frozen_manifest_sha256": sha256(args.frozen_manifest) if args.frozen_manifest else None,
    }
    artifact = args.output / "replay"
    if not args.recheck:
        _, handles = rescue_runtime.activate_onnx(
            args.ort_runtime, args.cuda_libraries, args.cudnn_directory
        )
        try:
            v0_replay.run(config, artifact, "OFFLINE_REPLAY", 600)
        finally:
            for handle in handles:
                handle.close()
    manifest = json.loads((artifact / "manifest.json").read_text())
    counts = manifest["session"]["summary"]["frame_counts"]
    if (
        manifest["status"] != "COMPLETE"
        or counts["processed"] != 18_000
        or counts["failed"]
        or counts["accepted"] != 18_000
        or counts["dropped"] != 1
        or counts["source"] != 18_001
        or manifest["session"]["summary"]["drops"] != {"USER_SKIP": 1}
        or manifest["source_end_observed_ns"] != 600_000_000_000
    ):
        raise RuntimeError("Canonical 18K coverage gate failed")
    identities = hashlib.sha256()
    rows = 0
    physical = Counter()
    levels = Counter()
    with (artifact / "updates.jsonl").open(encoding="utf-8") as trace:
        for line in trace:
            row = json.loads(line)
            identity = row["identity"]
            if (
                identity["sequence"] != rows
                or identity["observation_ns"] != rows * 1_000_000_000 // 30
            ):
                raise ValueError("Canonical sequence or PTS mismatch")
            identities.update(f"{rows}:{identity['observation_ns']}\n".encode())
            for stage, items in (
                ("world", "entities"),
                ("tracks", "tracks"),
                ("corridor_analysis", "entity_relations"),
                ("trajectory_set", "trajectories"),
                ("interaction_analysis", "entity_interactions"),
                ("risk_assessment_set", "assessments"),
                ("attention_decision_set", "selected"),
            ):
                physical[stage] += len((row[stage] or {}).get(items, []))
            for alert in (row["alert_output_set"] or {}).get("outputs", []):
                if alert["delivered"]:
                    levels[alert["presentation"].get("semantic_level", "UNRECORDED")] += 1
            rows += 1
    if rows != 18_000:
        raise ValueError("Canonical trace count mismatch")
    report = dict(
        provenance,
        stage_item_counts=physical,
        text_sink_acceptances_by_recorded_level=levels,
        frame_counts=counts,
        excluded_end_boundary_ns=600_000_000_000,
        identity_sha256=identities.hexdigest(),
        source_sha256=manifest["source_sha256"],
    )
    with (args.output / "qualification.json").open("x", encoding="utf-8") as result:
        json.dump(report, result, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in (
        "checkout",
        "config",
        "output",
        "ort-runtime",
        "cuda-libraries",
        "cudnn-directory",
    ):
        parser.add_argument("--" + argument, type=Path, required=True)
    parser.add_argument("--frozen-manifest", type=Path)
    parser.add_argument("--recheck", action="store_true")
    run(parser.parse_args())
