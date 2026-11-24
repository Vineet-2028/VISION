"""Reproducible read-only source classification and exclusive V0 baseline snapshot."""

import hashlib
import json
import re
import subprocess
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TERMS = re.compile(
    r"\b(person|car|truck|bus|bicycle|motorcycle|dog|cat|vehicle|COCO|class_id|class_name)\b",
    re.IGNORECASE,
)
TEXT = {
    ".py",
    ".java",
    ".kt",
    ".kts",
    ".ts",
    ".tsx",
    ".mjs",
    ".json",
    ".md",
    ".yaml",
    ".yml",
    ".xml",
    ".toml",
    ".html",
    ".css",
    ".properties",
    ".ps1",
}


def classification(name: str) -> tuple[str, str]:
    path = Path(name)
    if "/test" in name or name.startswith("tests/"):
        return (
            "LEGITIMATE TEST FIXTURE",
            "Test population or assertion; preserve fixtures",
        )
    if name.startswith(("configs/", "datasets/")) or path.suffix in {
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".xml",
        ".properties",
        ".kts",
    }:
        return "CONFIGURATION", "Versioned data/build/schema or evaluation evidence"
    if path.suffix == ".md" or name.startswith("apps/web/"):
        return "DISPLAY COPY", "Documentation or presentation; no risk rule"
    if name.startswith("tools/") or any(
        v in path.stem
        for v in (
            "benchmark",
            "evaluation",
            "dataset",
            "metrics",
            "parity",
            "first_person",
        )
    ):
        return (
            "CONFIGURATION",
            "Evaluation taxonomy/proxy population; not realtime policy",
        )
    return (
        "ARCHITECTURAL HARD-CODING",
        "Runtime occurrence requiring boundary review; not automatically a defect",
    )


def main() -> None:
    names = sorted(
        set(
            subprocess.check_output(
                ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                cwd=ROOT,
                text=True,
            ).splitlines()
        )
    )
    files = []
    occurrences = []
    for name in names:
        path = ROOT / name
        if (
            not path.is_file()
            or path.suffix.lower() not in TEXT
            or path.name == "package-lock.json"
        ):
            continue
        if not path.resolve().is_relative_to(ROOT):
            raise ValueError("Source path escapes repository")
        content = path.read_text(encoding="utf-8-sig")
        files.append(name)
        kind, rationale = classification(name)
        for number, line in enumerate(content.splitlines(), 1):
            if TERMS.search(line):
                occurrences.append(
                    {
                        "path": name,
                        "line": number,
                        "classification": kind,
                        "rationale": rationale,
                        "matched_terms": TERMS.findall(line),
                    }
                )
    frozen = json.loads((ROOT / "benchmark-results/v0-field/frozen-v0.json").read_text())
    for name, expected in frozen.items():
        with (ROOT / name).open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                raise ValueError(f"Frozen rescue changed: {name}")
    target = ROOT / "benchmark-results/v02/VISION_V0_RESCUED_BASELINE"
    target.mkdir(parents=True, exist_ok=False)
    hashes = {}
    # Includes pre-existing working changes: HEAD alone is not this rescued baseline.
    with zipfile.ZipFile(target / "sources.zip", "x", zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            data = (ROOT / name).read_bytes()
            hashes[name] = hashlib.sha256(data).hexdigest()
            archive.writestr(name, data)
        for name in ("package-lock.json", "package.json"):
            if name not in hashes:
                data = (ROOT / name).read_bytes()
                hashes[name] = hashlib.sha256(data).hexdigest()
                archive.writestr(name, data)
    manifest = {
        "name": "VISION_V0_RESCUED_BASELINE",
        "date": "2026-10-27",
        "source_hashes": hashes,
        "frozen_rescue_references": frozen,
        "binary_assets": "Remain in original ignored paths; never overwritten",
        "classification_counts": dict(Counter(r["classification"] for r in occurrences)),
        "files_scanned": len(files),
        "matching_lines": len(occurrences),
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (target / "occurrences.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in occurrences), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "baseline": str(target),
                "files": len(files),
                "matches": len(occurrences),
                "counts": manifest["classification_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
