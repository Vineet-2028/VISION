"""Freeze the measured local Alpha engine and its evidence after the engine gates pass."""

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def freeze(root, evidence, verify_log, output):
    hashes = {}

    def record(name):
        path = evidence / name
        hashes[name] = digest(path)
        return json.loads(path.read_text(encoding="utf-8"))

    rt = record("alpha-full-realtime-01/manifest.json")
    report = record("alpha-full-realtime-01-report.json")
    process = record("alpha-full-realtime-01-process/process-summary.json")
    pair = record("alpha-compute-batch-02/paired-result.json")
    selection = record("alpha-compute-batch-02/candidate-selection.json")
    rotated = record("alpha-rotated-suite-01/suite.json")
    baseline = record("alpha-offline-18k-baseline-01/qualification.json")
    candidate = record("alpha-offline-18k-candidate-02/qualification.json")
    comparison = record("alpha-offline-18k-comparison-01.json")
    profile = record("alpha-candidate-profile-02.json")
    gpu = record("alpha-gpu-optimization-02/report.json")
    hardware = record("alpha-release-completion-hardware-01.json")
    check_log = verify_log.read_text(encoding="utf-8")
    if not all(
        (
            "PASS: API contracts, production home" in check_log,
            "No npm advisories reported." in check_log,
            process["status"] == "EXITED_SUCCESS",
            rt["status"] == "COMPLETE",
            rt["source_end_observed_ns"] >= 1_498_000_000_000,
            report["source_sha256"]
            == rt["source_sha256"]
            == baseline["source_sha256"]
            == candidate["source_sha256"],
            baseline["identity_sha256"]
            == candidate["identity_sha256"]
            == comparison["identity_sha256"],
            baseline["frame_counts"]["processed"]
            == candidate["frame_counts"]["processed"]
            == 18000,
            report["whole_run"]["counts"]["delivered_after_expiry"] == 0,
            report["whole_run"]["counts"]["unusable_view_output_violations"] == 0,
            report["whole_run"]["counts"]["update_errors"] == 0,
            report["trace_writer"]["dropped"] == report["frame_counts"]["failed"] == 0,
            report["peak_queue_depth"] <= 1,
            report["first_600_source_seconds"]["updates"] / 600 >= 4.399,
            report["first_600_source_seconds"]["publication_age"]["p95_ns"] <= 567_211_000,
            gpu["fp32_parity_passed"],
            pair["status"] == "PAIRED_PRESENTATION_ABLATION_VERIFIED",
            pair["updates_per_arm"] == 3000 and not pair["nonpresentation_differences"],
            selection["optional_semantic_enricher"] == "NONE",
            len(rotated["arms"]) == 21 and len(rotated["comparisons"]) == 7,
            all(
                arm["frame_counts"]["processed"] == 60 and not arm["frame_counts"]["failed"]
                for arm in rotated["arms"]
            ),
        )
    ):
        raise ValueError("An engine qualification gate is open")
    # The archived realtime runtime is the release source of truth. Field transport
    # and benchmark runners are separate consumers of the engine.
    archive = evidence / "alpha-full-realtime-01-runtime.zip"
    sources = rt["runtime_source_sha256"]
    with zipfile.ZipFile(archive) as zip_file:
        if set(zip_file.namelist()) != set(sources):
            raise ValueError("Archived runtime file set mismatch")
        for name, expected in sources.items():
            if hashlib.sha256(zip_file.read(name)).hexdigest() != expected:
                raise ValueError(f"Archived runtime hash mismatch: {name}")
            if not name.startswith("tools/") and not Path(name).name.startswith("field_"):
                if digest(root / name) != expected:
                    raise ValueError(f"Qualified engine source has changed: {name}")
    models = {}
    for provider in ("detector", "segmentation"):
        expected = profile[provider]["sha256"]
        if digest(Path(profile[provider]["weights"])) != expected:
            raise ValueError(f"{provider} model hash mismatch")
        models[provider] = expected
    manifest = {
        "release": "VISION_CONTROLLED_ALPHA_V1",
        "scope": "LOCAL_ENGINE_PROTOTYPE",
        "repository_head_at_freeze": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "runtime_sources": sources,
        "runtime_archive_sha256": digest(archive),
        "models": models,
        "ontology_sha256": digest(Path(profile["entity_semantics_ontology"])),
        "configuration": profile,
        "detector_runtime": rt["detector_runtime"],
        "hardware": hardware,
        "evidence_sha256": hashes,
        "verify_log_sha256": digest(verify_log),
        "field_qualification": "SEPARATE_GATE",
        "production_safety_validated": False,
    }
    output.mkdir(exist_ok=False)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--verify-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    freeze(Path(__file__).resolve().parents[1], args.evidence, args.verify_log, args.output)
