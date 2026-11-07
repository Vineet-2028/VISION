import cv2
import numpy as np
import pytest

from perception_lab.field_protocol import (
    PROTOCOL,
    ClockEstimate,
    FrameHeader,
    decode_frame,
    encode_frame,
    estimate_clock,
    strict_json,
)


def test_four_clock_exchange_retains_offset_uncertainty_and_refresh():
    estimate = estimate_clock(1000, 1110, 1120, 1030, 1)
    assert estimate.offset_ns == 100
    assert estimate.rtt_ns == 20 and estimate.uncertainty_ns == 10
    assert estimate.earliest_host_capture(1040, 1200) == 1130
    with pytest.raises(ValueError, match="EXPIRED"):
        estimate.uncertainty_at(20_000_000_000)
    assert estimate_clock(1000, 1210, 1220, 1230, 2).uncertainty_ns == 110


@pytest.mark.parametrize("delay_ms", [50, 100, 250, 500, 1000])
def test_network_delay_cannot_make_old_capture_fresh(delay_ms):
    delay = delay_ms * 1_000_000
    estimate = estimate_clock(
        1_000_000_000, 1_000_000_000 + delay, 1_000_000_000 + delay, 1_000_000_000 + 2 * delay, 1
    )
    if delay_ms >= 100:
        with pytest.raises(ValueError, match="UNCERTAIN"):
            estimate.earliest_host_capture(1_000_000_000, 2_100_000_000)
    else:
        assert estimate.earliest_host_capture(1_000_000_000, 2_100_000_000) < 1_000_000_000


def test_clock_order_and_future_capture_rejected():
    with pytest.raises(ValueError):
        estimate_clock(4, 4, 3, 5, 1)
    with pytest.raises(ValueError, match="FUTURE"):
        ClockEstimate(0, 0, 0, 100, 1).earliest_host_capture(500, 100)


def test_binary_frame_roundtrip_and_bounds():
    header = FrameHeader(
        protocol_version=PROTOCOL,
        session_id="fixture",
        sequence=7,
        camera_ns="100",
        capture_ns="101",
        send_ns="102",
        sync_version=1,
        rotation=90,
        width=640,
        height=480,
        format="JPEG",
        jpeg_quality=75,
    )
    ok, encoded = cv2.imencode(".jpg", np.zeros((480, 640, 3), dtype=np.uint8))
    assert ok
    image = encoded.tobytes()
    assert decode_frame(encode_frame(header, image)) == (header, image)
    with pytest.raises(ValueError, match="DIMENSIONS"):
        encode_frame(header.model_copy(update={"height": 64}), image)
    with pytest.raises(ValueError, match="UNSUPPORTED"):
        encode_frame(header, image[:-2] + image)
    with pytest.raises(ValueError, match="JPEG"):
        encode_frame(header, b"\xff\xd8fixture")
    for payload in [b"", b"\xff" * 20, b"x" * 600_000]:
        with pytest.raises(ValueError):
            decode_frame(payload)


@pytest.mark.parametrize("payload", [b'{"x":1,"x":2}', b'{"x":NaN}', b"[]"])
def test_json_rejects_ambiguous_or_nonfinite_payload(payload):
    with pytest.raises(ValueError):
        strict_json(payload)
