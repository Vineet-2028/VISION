from fractions import Fraction

import numpy as np
import pytest
from pydantic import ValidationError

from perception_lab.config import Calibration, LabConfig, read_json
from perception_lab.contracts import Frame, FrameIdentity, PixelFormat, TimingProvenance
from perception_lab.metrics import Distribution
from perception_lab.scheduling import FixedRateScheduler, FrameQueue, QueuedFrame
from perception_lab.sources import SyntheticSource, pts_to_ns


@pytest.mark.parametrize(
    "pts,base,expected",
    [
        (0, Fraction(1, 30), 0),
        (1, Fraction(1, 30), 33333333),
        (3003, Fraction(1, 90000), 33366666),
        (None, Fraction(1, 30), None),
        (-1, Fraction(1, 30), None),
        (1, None, None),
        (1, Fraction(0), None),
        (2**63, Fraction(1), None),
        (2**53 + 1, Fraction(1, 10**9), 2**53 + 1),
    ],
)
def test_rational_pts(pts, base, expected):
    assert pts_to_ns(pts, base) == expected


@pytest.mark.parametrize(
    "change",
    [
        {"queue_capacity": 0},
        {"queue_capacity": True},
        {"queue_capacity": 65},
        {"mode": "REALTIME"},
        {"drop_policy": "DROP_OLDEST"},
        {"unknown": 1},
        {"intervals_ns": {}},
        {"intervals_ns": {"detector": 0}},
        {"intervals_ns": {"risk": 10}},
        {"debug_every_n": 1},
        {"end_ns": 0},
        {"source_id": "C:/private/source"},
        {"visualization": "true"},
    ],
)
def test_config_rejects_invalid(config, change):
    with pytest.raises(ValidationError):
        LabConfig.model_validate({**config.model_dump(), **change})


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": 2},
        {"distortion_model": "fisheye"},
        {"distortion_coefficients": {"k1": 1.0}},
        {"resolution": {"width": 0, "height": 6}},
        {"intrinsics": {"fx": float("nan"), "fy": 8.0, "cx": 4.0, "cy": 3.0}},
        {
            "calibration_quality": {
                "state": "VALID",
                "rms_pixels": None,
                "sample_count": None,
                "timestamp_epoch_millis": None,
            }
        },
        {"pixel_convention": "integer_centers"},
        {"camera_frame_id": ""},
    ],
)
def test_invalid_calibration(calibration, change):
    with pytest.raises(ValidationError):
        Calibration.model_validate({**calibration.model_dump(), **change})


def test_duplicate_json_fields_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"a":1,"a":2}')
    with pytest.raises(ValueError, match="Duplicate"):
        read_json(path)


def test_buffer_format_and_immutability():
    frame = next(iter(SyntheticSource(iter([7]))))
    assert frame.identity.observation_ns == 7
    assert frame.pixel_format == PixelFormat.RGB
    assert frame.pixels.shape == (6, 8, 3)
    assert not frame.pixels.flags.writeable
    with pytest.raises(ValueError):
        Frame(frame.identity, np.zeros((6, 8, 1), dtype=np.uint8), PixelFormat.RGB, 0, 0)


def test_frame_identity_rejects_invalid():
    with pytest.raises(ValueError):
        FrameIdentity("s", 0, -1, TimingProvenance.SYNTHETIC)


def test_scheduler_vfr_no_accumulated_drift():
    scheduler = FixedRateScheduler({"detector": 100, "depth": 200})
    assert [scheduler.eligible(t) for t in (15, 45, 119, 314, 315, 499, 515)] == [
        ("detector", "depth"),
        (),
        ("detector",),
        ("detector", "depth"),
        ("detector",),
        ("detector", "depth"),
        ("detector",),
    ]
    assert scheduler.next_due == {"detector": 615, "depth": 615}
    with pytest.raises(ValueError):
        scheduler.eligible(515)


@pytest.mark.parametrize(
    "policy,remaining,dropped",
    [
        ("DROP_OLDEST", [7, 8, 9], 7),
        ("LATEST_FRAME", [9], 9),
    ],
)
def test_bounded_queue_fast_producer(policy, remaining, dropped):
    queue = FrameQueue(3, policy)
    evicted = []
    for frame in SyntheticSource(iter(range(10))):
        item = queue.offer(QueuedFrame(frame, 0, 0))
        if item:
            evicted.append(item.frame.identity.sequence)
    assert [i.frame.identity.sequence for i in queue.items] == remaining
    assert evicted == list(range(dropped))
    assert queue.peak <= 3


def test_offline_backpressure_never_overwrites():
    queue = FrameQueue(1, "PROCESS_ALL")
    frame = next(iter(SyntheticSource(iter([0]))))
    queue.offer(QueuedFrame(frame, 0, 0))
    with pytest.raises(BufferError):
        queue.offer(QueuedFrame(frame, 0, 0))
    assert len(queue.items) == 1
    assert queue.pop().frame is frame


def test_percentiles_are_nearest_rank_with_bounded_scope():
    distribution = Distribution(4)
    for value in range(1, 101):
        distribution.add(value)
    result = distribution.summary()
    assert result == {
        "count": 100,
        "min_ns": 1,
        "max_ns": 100,
        "mean_ns": 50.5,
        "percentile_scope": "recent_window",
        "window_count": 4,
        "p50_ns": 98,
        "p90_ns": 100,
        "p95_ns": 100,
        "p99_ns": 100,
    }
    assert Distribution(2).summary()["p50_ns"] is None
    with pytest.raises(ValueError):
        distribution.add(-1)
