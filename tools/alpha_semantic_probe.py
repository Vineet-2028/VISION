"""Real CPU PicoDet and full Guardian stages on exact population frames plus context.

This is a deterministic offline evidence probe, not realtime cadence qualification.
"""

import argparse
import bisect
import json
from pathlib import Path
from time import perf_counter_ns

import av
from v0_replay import TracePipeline, TraceRecorder
from v02_candidate_population import digest, source_targets

from perception_lab.config import Calibration, LabConfig
from perception_lab.contracts import Frame, FrameIdentity, PixelFormat, TimingProvenance
from perception_lab.edge_runtime import PicoDetDetector
from perception_lab.geometry import CoreGeometry
from perception_lab.preprocessing import BasicPreprocessor
from perception_lab.sources import pts_to_ns


class PopulationSource:
    def __init__(self, video, source_id, targets, deadline):
        self.video, self.source_id, self.targets = video, source_id, targets
        self.exact = set(targets)
        self.seen = set()
        self.deadline = deadline
        self.frames = 0

    def __iter__(self):
        import psutil

        last = -1_000_000_000
        with (
            self.video.open("rb") as source,
            av.open(
                source, options={"format_whitelist": "mov", "protocol_whitelist": "file"}
            ) as container,
        ):
            stream = container.streams.video[0]
            stream.codec_context.thread_count = 1
            for sequence, native in enumerate(container.decode(stream)):
                stamp = pts_to_ns(native.pts, native.time_base)
                if stamp is None or native.is_corrupt:
                    raise ValueError("Invalid source frame; no substitution")
                index = bisect.bisect_left(self.targets, stamp)
                if index == len(self.targets):
                    break
                exact = stamp in self.exact
                context = self.targets[index] - stamp <= 800_000_000 and stamp - last >= 200_000_000
                if not exact and not context:
                    continue
                if (
                    perf_counter_ns() >= self.deadline
                    or psutil.virtual_memory().available < 2 * 1024**3
                ):
                    raise RuntimeError("Probe time or RAM budget exhausted; incomplete")
                now = perf_counter_ns()
                pixels = native.to_ndarray(format="rgb24")
                self.frames += 1
                if self.frames > 2200:
                    raise RuntimeError("Context frame bound exceeded")
                last = stamp
                if exact:
                    self.seen.add(stamp)
                yield Frame(
                    FrameIdentity(
                        self.source_id, sequence, stamp, TimingProvenance.AUTHORITATIVE_PTS
                    ),
                    pixels,
                    PixelFormat.RGB,
                    now,
                    perf_counter_ns(),
                )
        if self.seen != self.exact:
            raise ValueError("Not every exact population frame was decoded")

    def close(self):
        pass  # Generator's context managers own local decoder/file handles.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    population_path = root / "benchmark-results/v02/populations-02.json"
    population = json.loads(population_path.read_text())
    raw = json.loads(
        (
            root / "benchmark-results/v0-rescue/realtime-06-gpu-no-depth/configuration.json"
        ).read_text()
    )
    video = Path(raw["input"])
    if digest(video) != population["source_sha256"]:
        raise ValueError("Source hash mismatch")
    ontology = root / "configs/perception/ontology/vision-domain-v2.json"
    raw.update(
        mode="OFFLINE_REPLAY",
        realtime_rescue=False,
        drop_policy="PROCESS_ALL",
        max_staleness_ns=None,
        start_ns=0,
        end_ns=None,
        record_session=False,
        visualization=False,
        output=str(args.output.resolve()),
        entity_semantics_ontology=str(ontology),
        depth=None,
        motion=None,
        segmentation=None,
        intervals_ns={"detector": 1},
    )
    raw["detector"].update(device="cpu", threads=2)
    config = LabConfig.model_validate(raw)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "configuration.json").write_text(json.dumps(config.model_dump(), indent=2))
    calibration = Calibration.model_validate_json(Path(config.calibration).read_text())
    geometry = CoreGeometry(calibration)
    detector = PicoDetDetector(
        Path(config.detector.weights),
        config.detector.sha256,
        confidence=config.detector.confidence,
        threads=2,
    )
    detector.enable_entity_semantics(ontology)
    source = PopulationSource(
        video,
        config.source_id,
        source_targets(population),
        perf_counter_ns() + 20 * 60 * 1_000_000_000,
    )
    recorder = TraceRecorder(config, calibration, args.output)
    with (args.output / "updates.jsonl").open("x") as trace:
        pipeline = TracePipeline(
            config,
            BasicPreprocessor(geometry, config.preprocess),
            recorder,
            detector=detector,
            motion_geometry=geometry,
            trace=trace,
        )
        summary = pipeline.run(source)
    report = {
        "status": "COMPLETE_OFFLINE_CONTEXT_PROBE_NOT_REALTIME_QUALIFICATION",
        "population_sha256": digest(population_path),
        "source_sha256": population["source_sha256"],
        "ontology_sha256": digest(ontology),
        "exact_frames": len(source.seen),
        "context_and_exact_frames": source.frames,
        "model_sha256": config.detector.sha256,
        "runtime": detector.runtime_metadata,
        "updates_sha256": digest(args.output / "updates.jsonl"),
        "summary": summary,
        "limitations": [
            "0.8 second preceding context sampled at 200 ms; every exact target forced",
            "Motion/segmentation disabled; reasoning retains unavailable evidence",
            "Not original realtime schedule or independent accuracy measurement",
        ],
    }
    (args.output / "probe-summary.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"exact_frames": len(source.seen), "total_frames": source.frames}), flush=True)


if __name__ == "__main__":
    main()
