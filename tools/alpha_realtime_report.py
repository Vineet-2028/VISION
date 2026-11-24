"""Summarize compact realtime traces by source PTS, using bounded per-frame memory."""

import argparse
import json
from collections import Counter
from pathlib import Path

from v0_analyze import quantiles


class Window:
    def __init__(self):
        self.ages = []
        self.alert_ages = []
        self.counts = Counter(delivered_after_expiry=0, unusable_view_output_violations=0)
        self.semantics = Counter()
        self.alert_levels = Counter()
        self.view = Counter()
        self.heading = Counter()
        self.orientation = Counter()
        self.capability = Counter()
        self.providers = Counter()
        self.first = self.last = None

    def observe(self, row):
        pts = row["identity"]["observation_ns"]
        if self.last is not None and pts <= self.last:
            raise ValueError("Realtime observations must advance")
        self.first = pts if self.first is None else self.first
        self.last = pts
        self.ages.append(row["source_to_publication_age_ns"])
        self.counts["update_errors"] += len(row["errors"])
        self.view[(row["camera_view_quality"] or {}).get("status", "UNAVAILABLE")] += 1
        self.heading[(row["user_motion_heading"] or {}).get("source", "UNAVAILABLE")] += 1
        self.orientation[(row["camera_orientation"] or {}).get("source", "UNAVAILABLE")] += 1
        self.capability[row["scene_capability"]] += 1
        for name, state in row["provider_state"].items():
            self.providers[f"{name}/{state['runtime']}"] += 1
        for issue in (row["tracks"] or {}).get("diagnostics", []):
            if "GAP" in issue and "RESET" in issue:
                self.counts["tracking_gap_reset_diagnostics"] += 1
        for key in (
            "tracks",
            "world",
            "corridor_analysis",
            "trajectory_set",
            "interaction_analysis",
            "risk_assessment_set",
            "attention_decision_set",
            "alert_output_set",
        ):
            self.counts[key] += row[key] is not None
        for entity in (row["world"] or {}).get("entities", []):
            state = entity["track_semantics"] or {}
            specific = state.get("quality") == "STABLE" and pts < (state.get("valid_until_ns") or 0)
            group = state.get("group_quality") == "STABLE" and pts < (
                state.get("group_valid_until_ns") or 0
            )
            self.semantics["specific" if specific else "group" if group else "unresolved"] += 1
        alerts = row["alert_output_set"] or {}
        if (row["camera_view_quality"] or {}).get("status") == "UNUSABLE":
            if row["scene_capability"] != "CAMERA_UNUSABLE" or any(
                item["delivered"] for item in alerts.get("outputs", [])
            ):
                self.counts["unusable_view_output_violations"] += 1
        self.counts["upstream_expired_candidates"] += alerts.get("upstream_expired_candidates", 0)
        for alert in alerts.get("outputs", []):
            if alert["delivered"]:
                presentation = alert["presentation"]
                self.alert_levels[presentation["semantic_level"]] += 1
                deadline = min(alert["intent"]["valid_until_ns"], presentation["valid_until_ns"])
                self.counts["delivered_after_expiry"] += alert["delivery_timestamp"] >= deadline
                if alert["source_age_at_delivery_ns"] is not None:
                    self.alert_ages.append(alert["source_age_at_delivery_ns"])

    def report(self):
        return {
            "updates": len(self.ages),
            "first_source_ns": self.first,
            "last_source_ns": self.last,
            "publication_age": quantiles(self.ages),
            "source_to_text_sink_age": quantiles(self.alert_ages),
            "counts": self.counts,
            "world_entity_observations_by_best_fresh_level": self.semantics,
            "text_sink_acceptances_by_level": self.alert_levels,
            "view_status": self.view,
            "heading_source": self.heading,
            "orientation_source": self.orientation,
            "scene_capability": self.capability,
            "provider_runtime_updates": self.providers,
        }


def summarize(directory):
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest["status"] != "COMPLETE" or manifest["mode"] != "REALTIME":
        raise ValueError("A completed realtime run is required")
    whole, canonical = Window(), Window()
    with (directory / "updates.jsonl").open(encoding="utf-8") as trace:
        for line in trace:
            row = json.loads(line)
            whole.observe(row)
            if row["identity"]["observation_ns"] < 600_000_000_000:
                canonical.observe(row)
    summary = manifest["session"]["summary"]
    if (
        len(whole.ages) != summary["frame_counts"]["processed"]
        or len(whole.ages) != manifest["trace_writer"]["rows"]
    ):
        raise ValueError("Trace count differs from pipeline or writer")
    return {
        "source_sha256": manifest["source_sha256"],
        "configuration_sha256": manifest["configuration_sha256"],
        "whole_run": whole.report(),
        "first_600_source_seconds": canonical.report(),
        "acquisition": summary["acquisition"],
        "effective_output_fps": summary["effective_output_fps"],
        "peak_queue_depth": summary["peak_queue_depth"],
        "frame_counts": summary["frame_counts"],
        "trace_writer": manifest["trace_writer"],
        "peak_sampled_rss_bytes": manifest["memory"]["peak_sampled"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = summarize(args.directory)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2)
