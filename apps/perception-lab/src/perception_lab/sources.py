"""Decoder boundary. Only local file handles reach FFmpeg; never URLs or playlists."""

from collections.abc import Callable, Iterator
from fractions import Fraction
from pathlib import Path
from typing import Protocol, cast

import av
import numpy as np
from numpy.typing import NDArray

from .clocks import processing_ns
from .contracts import (
    DropReason,
    Frame,
    FrameIdentity,
    LabError,
    PixelFormat,
    SourceIssue,
    TimingProvenance,
)


class FrameSource(Protocol):
    def __iter__(self) -> Iterator[Frame | SourceIssue]: ...
    def close(self) -> None: ...


def pts_to_ns(pts: int | None, time_base: Fraction | None) -> int | None:
    """Rational conversion, floor to integer ns (error <1ns), no float seconds."""
    if pts is None or time_base is None or time_base <= 0:
        return None
    ns = pts * time_base.numerator * 1_000_000_000 // time_base.denominator
    return ns if 0 <= ns <= 2**63 - 1 else None


class VideoFileSource:
    def __init__(self, path: Path, source_id: str, max_pixels: int) -> None:
        if not path.is_file():
            raise LabError("SOURCE_NOT_FILE")
        self.source_id = source_id
        self.max_pixels = max_pixels
        self.closed = False
        self.realtime_minimum_ns: Callable[[], int] | None = None
        self.skipped_conversion = 0
        # Restrict demuxers to local self-contained formats; manifests can reference URLs.
        self._file = path.open("rb")
        try:
            self._container = av.open(
                self._file,
                mode="r",
                options={"format_whitelist": "mov,matroska,webm,avi", "protocol_whitelist": "file"},
            )
            if not self._container.streams.video:
                raise LabError("NO_VIDEO_STREAM")
            self._stream = self._container.streams.video[0]
            self._stream.codec_context.thread_count = 1
        except BaseException as error:
            try:
                if hasattr(self, "_container"):
                    self._container.close()
            finally:
                self._file.close()
            if isinstance(error, KeyboardInterrupt):
                raise
            raise LabError("SOURCE_OPEN_FAILED") from None

    def __iter__(self) -> Iterator[Frame | SourceIssue]:
        sequence = 0
        last_ns = -1
        try:
            for packet in self._container.demux(self._stream):
                started = processing_ns()
                try:
                    decoded = packet.decode()
                except av.error.InvalidDataError:
                    # Packet failure has unknown frame multiplicity. Count one decode issue.
                    yield SourceIssue(sequence, DropReason.DECODE_FAILURE)
                    sequence += 1
                    continue
                for native in decoded:
                    completed = processing_ns()
                    ns = pts_to_ns(native.pts, native.time_base)
                    reason = None
                    if native.is_corrupt:
                        reason = DropReason.CORRUPT_FRAME
                    elif ns is None or ns <= last_ns:
                        reason = DropReason.INVALID_TIMESTAMP
                    if reason is not None:
                        yield SourceIssue(sequence, reason)
                    else:
                        assert ns is not None
                        last_ns = ns
                        if native.width * native.height > self.max_pixels:
                            raise LabError("FRAME_SIZE_LIMIT")
                        if self.realtime_minimum_ns is not None and ns < self.realtime_minimum_ns():
                            self.skipped_conversion += 1
                            sequence += 1
                            started = processing_ns()
                            continue
                        conversion_start = processing_ns()
                        pixels = cast(NDArray[np.uint8], native.to_ndarray(format="rgb24"))
                        conversion_ns = processing_ns() - conversion_start
                        yield Frame(
                            FrameIdentity(
                                self.source_id, sequence, ns, TimingProvenance.AUTHORITATIVE_PTS
                            ),
                            pixels,
                            PixelFormat.RGB,
                            started,
                            completed,
                            conversion_ns,
                        )
                    sequence += 1
                    # A packet may release multiple delayed frames: do not charge decoding twice.
                    started = processing_ns()
        except av.error.FFmpegError:
            raise LabError("DECODE_FATAL") from None

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            try:
                self._container.close()
            finally:
                self._file.close()


class SyntheticSource:
    """Lazy test source; constant image allocation per yielded frame, no retained history."""

    def __init__(
        self,
        timestamps: Iterator[int],
        width: int = 8,
        height: int = 6,
        source_id: str = "synthetic",
    ) -> None:
        self.timestamps = timestamps
        self.width, self.height, self.source_id = width, height, source_id
        self.closed = False

    def __iter__(self) -> Iterator[Frame | SourceIssue]:
        for sequence, ns in enumerate(self.timestamps):
            now = processing_ns()
            yield Frame(
                FrameIdentity(self.source_id, sequence, ns, TimingProvenance.SYNTHETIC),
                np.zeros((self.height, self.width, 3), dtype=np.uint8),
                PixelFormat.RGB,
                now,
                now,
            )

    def close(self) -> None:
        self.closed = True
