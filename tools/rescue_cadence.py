"""Sequential, versioned short cadence experiments on the canonical source.

These pilots select engineering configurations; they do not replace the full
600-second qualification or change its reference population.
"""

import argparse
import gc
import json
from pathlib import Path


def run(config_path, output, seconds):
    from v0_replay import run as replay

    output.mkdir(parents=True, exist_ok=False)
    base = json.loads(config_path.read_text())
    experiments = [
        ("detector-2", 2, 1, 1, 5),
        ("detector-5", 5, 1, 1, 5),
        ("detector-10", 10, 1, 1, 5),
        ("depth-2", 5, 2, 1, 5),
        ("depth-5", 5, 5, 1, 5),
        ("semantic-half", 5, 1, 0.5, 5),
        ("semantic-2", 5, 1, 2, 5),
        ("image-space-degraded", 5, None, 0.5, 5),
        ("detector-only-degraded", 5, None, None, None),
    ]
    matrix = []
    for name, detector, depth, semantic, flow in experiments:
        raw = json.loads(json.dumps(base))
        raw["realtime_rescue"] = True
        rates = {
            "detector": detector,
            "depth": depth,
            "segmentation": semantic,
            "optical_flow": flow,
        }
        raw["intervals_ns"] = {
            key: int(1e9 / rate) for key, rate in rates.items() if rate is not None
        }
        for key, rate in (("depth", depth), ("segmentation", semantic), ("motion", flow)):
            if rate is None:
                raw[key] = None
        config = output / (name + ".json")
        config.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        destination = output / name
        print("Starting " + name, flush=True)
        replay(config, destination, "REALTIME", seconds)
        result = json.loads((destination / "manifest.json").read_text())
        summary = result["session"]["summary"]
        matrix.append(
            {
                "name": name,
                "requested_hz": rates,
                "status": result["status"],
                "counts": summary["frame_counts"],
                "intervals": result["update_intervals"],
                "publication_age": summary["timing"]["realtime_result_age"],
                "tracking": summary["tracking_peaks"],
                "memory": result["memory"],
                "enrichment_rejections": summary.get("enrichment_rejections"),
                "configuration": str(config),
            }
        )
        (output / "matrix.json").write_text(json.dumps(matrix, indent=2), encoding="utf-8")
        gc.collect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=15)
    args = parser.parse_args()
    if not 5 <= args.seconds <= 60:
        parser.error("Pilot seconds must be between 5 and 60")
    run(args.config, args.output, args.seconds)
