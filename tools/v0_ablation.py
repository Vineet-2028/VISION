"""Bounded cumulative stage ablation. No model replacements or policy tuning."""

import argparse
import json
from pathlib import Path

from v0_replay import run

PROFILES = (
    ("A_decode", ()),
    ("B_detector", ("detector",)),
    ("C_tracker", ("detector", "tracker")),
    ("D_depth", ("detector", "tracker", "depth")),
    ("E_motion", ("detector", "tracker", "depth", "motion")),
    ("F_semantics", ("detector", "tracker", "depth", "motion", "segmentation")),
    ("G_world", ("detector", "tracker", "depth", "motion", "segmentation", "world_model")),
    (
        "H_reasoning",
        (
            "detector",
            "tracker",
            "depth",
            "motion",
            "segmentation",
            "world_model",
            "corridor",
            "trajectory",
            "interaction",
            "risk",
            "attention",
            "alerts",
        ),
    ),
)


def ablate(config_path, output, seconds=3):
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    base = config_path.resolve().parent
    for key in ("input", "calibration", "output"):
        raw[key] = str((base / raw[key]).resolve())
    for key in ("detector", "depth", "segmentation"):
        if raw.get(key) and raw[key].get("weights"):
            raw[key]["weights"] = str((base / raw[key]["weights"]).resolve())
    output.mkdir(parents=True, exist_ok=False)
    reports = []
    for name, enabled in PROFILES:
        profile = dict(raw)
        for key in PROFILES[-1][1]:
            profile[key] = raw.get(key) or {} if key in enabled else None
        path = output / f"{name}.json"
        path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
        run(path, output / name, "OFFLINE_REPLAY", seconds, full_stack=False)
        result = json.loads((output / name / "manifest.json").read_text(encoding="utf-8"))
        reports.append({"profile": name, "enabled": enabled, "result": result})
    (output / "summary.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_seconds_each": seconds,
                "profiles": reports,
                "limitations": [
                    "One pass in fixed order; startup/cache/load confounded",
                    "Diagnostic isolation only; not a statistically established speedup",
                    "All providers and thresholds unchanged; cumulative profiles",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 10:
        parser.error("Bounded ablation requires 1-10 source seconds")
    ablate(args.config, args.output, args.seconds)
