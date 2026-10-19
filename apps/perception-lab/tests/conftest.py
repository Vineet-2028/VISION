import json
from pathlib import Path

import pytest

from perception_lab.config import Calibration, LabConfig, read_json
from perception_lab.geometry import CoreGeometry
from perception_lab.pipeline import Pipeline
from perception_lab.preprocessing import BasicPreprocessor
from perception_lab.recording import SessionRecorder

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def calibration():
    return Calibration.model_validate(
        read_json(ROOT / "configs/calibration.synthetic.example.json")
    )


@pytest.fixture
def geometry(calibration):
    return CoreGeometry(calibration)


@pytest.fixture
def config():
    return LabConfig(
        input="test.mkv",
        calibration="test.json",
        source_id="synthetic",
        intervals_ns={"detector": 10, "depth": 20, "segmentation": 30, "optical_flow": 10},
    )


@pytest.fixture
def make_pipeline(config, calibration, geometry, tmp_path):
    def make(changes=None, **kwargs):
        cfg = LabConfig.model_validate({**config.model_dump(), **(changes or {})})
        recorder = SessionRecorder(cfg, calibration, tmp_path)
        pipeline = Pipeline(cfg, BasicPreprocessor(geometry, cfg.preprocess), recorder, **kwargs)
        return pipeline, recorder

    return make


def records(recorder):
    return [
        json.loads(line) for line in (recorder.directory / "frames.jsonl").read_text().splitlines()
    ]
