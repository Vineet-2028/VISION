"""Versioned field transport boundaries; no inference objects or clock guessing."""

import json
import re
import struct
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

PROTOCOL = "VISION_FIELD_PROTOCOL_V1"
MAX_FRAME_BYTES = 512_000
MAX_HEADER_BYTES = 4096
MAX_SYNC_AGE_NS = 15_000_000_000
MAX_SYNC_UNCERTAINTY_NS = 100_000_000
Ns = Annotated[str, Field(pattern=r"^(0|[1-9][0-9]{0,18})$")]
Id = Annotated[str, Field(pattern=r"^[A-Za-z0-9_.-]{1,96}$")]
Finite = Annotated[float, Field(allow_inf_nan=False)]


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class SessionStart(WireModel):
    protocol_version: Literal["VISION_FIELD_PROTOCOL_V1"]
    client_version: Id
    device_id: Id  # Random per session, never hardware/account identity.
    mode: Literal["ANDROID_FIELD_HARNESS", "DESKTOP_REALTIME"]
    width: Annotated[int, Field(ge=32, le=1280)]
    height: Annotated[int, Field(ge=32, le=1280)]
    format: Literal["JPEG"]
    capabilities: Annotated[
        list[Literal["TTS", "CAMERA_REALTIME_CLOCK", "NO_AUDIO"]], Field(max_length=3)
    ]


class PhoneSensors(WireModel):
    mount_clockwise_degrees: Literal[0, 90, 180, 270]
    gravity_ns: Ns | None = None
    gravity_device: Annotated[list[Finite], Field(min_length=3, max_length=3)] | None = None
    rotation_ns: Ns | None = None
    rotation_xyzw: Annotated[list[Finite], Field(min_length=4, max_length=4)] | None = None


class FrameHeader(WireModel):
    protocol_version: Literal["VISION_FIELD_PROTOCOL_V1"]
    session_id: Id
    sequence: Annotated[int, Field(ge=0, le=2**53 - 1)]
    camera_ns: Ns
    capture_ns: Ns
    send_ns: Ns
    sync_version: Annotated[int, Field(ge=1)]
    rotation: Literal[0, 90, 180, 270]
    width: Annotated[int, Field(ge=32, le=1280)]
    height: Annotated[int, Field(ge=32, le=1280)]
    format: Literal["JPEG"]
    jpeg_quality: Annotated[int, Field(ge=1, le=100)]
    sensors: PhoneSensors | None = None


_SCAN_MARKER = re.compile(rb"\xff(?=[^\x00\xff\xd0-\xd7])")


def check_camera_jpeg(image: bytes, width: int, height: int) -> None:
    """Accept a single baseline camera scan and bind native allocation to wire dimensions."""
    if not image.startswith(b"\xff\xd8") or not image.endswith(b"\xff\xd9"):
        raise ValueError("JPEG_REQUIRED")
    offset = 2
    seen_frame = False
    while offset < len(image) - 2:
        if image[offset] != 255:
            break
        while offset < len(image) and image[offset] == 255:
            offset += 1
        if offset + 3 > len(image):
            break
        marker = image[offset]
        length = int.from_bytes(image[offset + 1 : offset + 3], "big")
        end = offset + 1 + length
        if length < 2 or end > len(image) - 2:
            break
        if marker == 0xC0:
            if seen_frame or length < 11:
                break
            precision, rows, cols, channels = struct.unpack_from(">BHHB", image, offset + 3)
            if (cols, rows) != (width, height):
                raise ValueError("JPEG_DIMENSIONS_MISMATCH")
            if precision != 8 or channels not in (1, 3) or length != 8 + 3 * channels:
                break
            seen_frame = True
        elif marker == 0xDA:
            if length < 8 or length != 6 + 2 * image[offset + 3] or end >= len(image) - 2:
                break
            next_marker = _SCAN_MARKER.search(image, end)
            if seen_frame and next_marker and next_marker.start() == len(image) - 2:
                return
            break
        elif marker not in (0xC4, 0xDB, 0xDD, 0xFE) and not 0xE0 <= marker <= 0xEF:
            break
        offset = end
    raise ValueError("UNSUPPORTED_CAMERA_JPEG")


def decode_frame(payload: bytes) -> tuple[FrameHeader, bytes]:
    if not 6 <= len(payload) <= MAX_FRAME_BYTES + MAX_HEADER_BYTES + 4:
        raise ValueError("FRAME_SIZE")
    size = struct.unpack("!I", payload[:4])[0]
    if not 1 <= size <= MAX_HEADER_BYTES or size + 6 > len(payload):
        raise ValueError("HEADER_SIZE")
    header = FrameHeader.model_validate(strict_json(payload[4 : 4 + size], MAX_HEADER_BYTES))
    image = payload[4 + size :]
    if len(image) > MAX_FRAME_BYTES:
        raise ValueError("FRAME_SIZE")
    check_camera_jpeg(image, header.width, header.height)
    if not 0 <= int(header.camera_ns) <= int(header.capture_ns) <= int(header.send_ns) < 2**63:
        raise ValueError("CLIENT_CLOCK_ORDER")
    return header, image


def encode_frame(header: FrameHeader, image: bytes) -> bytes:
    encoded = header.model_dump_json().encode()
    result = struct.pack("!I", len(encoded)) + encoded + image
    decode_frame(result)
    return result


@dataclass(frozen=True)
class ClockEstimate:
    """host = client + offset. Bounds include path asymmetry and drift allowance."""

    offset_ns: int
    uncertainty_ns: int
    rtt_ns: int
    measured_host_ns: int
    version: int

    def uncertainty_at(self, now_host_ns: int) -> int:
        age = now_host_ns - self.measured_host_ns
        if age < 0 or age > MAX_SYNC_AGE_NS:
            raise ValueError("CLOCK_SYNC_EXPIRED")
        return self.uncertainty_ns + age // 1000  # Explicit conservative 1000 ppm budget.

    def earliest_host_capture(self, client_ns: int, now_host_ns: int) -> int:
        uncertainty = self.uncertainty_at(now_host_ns)
        if uncertainty > MAX_SYNC_UNCERTAINTY_NS:
            raise ValueError("CLOCK_SYNC_UNCERTAIN")
        mapped = client_ns + self.offset_ns
        if mapped - uncertainty > now_host_ns:
            raise ValueError("FUTURE_CAPTURE")
        return max(0, mapped - uncertainty)


def estimate_clock(t0: int, t1: int, t2: int, t3: int, version: int) -> ClockEstimate:
    if min(t0, t1, t2, t3) < 0 or t3 < t0 or t2 < t1 or version < 1:
        raise ValueError("CLOCK_ORDER")
    rtt = (t3 - t0) - (t2 - t1)
    if rtt < 0 or rtt > 2_000_000_000:
        raise ValueError("CLOCK_RTT")
    offset = ((t1 - t0) + (t2 - t3)) // 2
    return ClockEstimate(offset, (rtt + 1) // 2, rtt, t2, version)


def strict_json(data: bytes, limit: int = 16_384) -> dict[str, object]:
    if len(data) > limit:
        raise ValueError("JSON_SIZE")

    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in items:
            if key in result:
                raise ValueError("DUPLICATE_KEY")
            result[key] = value
        return result

    value: object = json.loads(
        data,
        object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("FINITE_JSON")),
    )
    if not isinstance(value, dict):
        raise ValueError("JSON_OBJECT_REQUIRED")
    return value
