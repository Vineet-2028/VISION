"""Paced replay acquisition with exactly one newest pending frame.

This adapter is realtime-only. It owns iteration and cleanup on one thread.
Decoder errors are never replaced by newer frames.
"""

from collections.abc import Iterator
from threading import Condition, Event, Thread
from time import perf_counter_ns

from .contracts import Frame, LabError, SourceIssue
from .metrics import Distribution
from .sources import FrameSource, VideoFileSource


class LatestSource:
    def __init__(self, source: FrameSource, start_ns: int, end_ns: int | None) -> None:
        self.source, self.start_ns, self.end_ns = source, start_ns, end_ns
        self.anchor_ns: int | None = None
        self.observation_anchor = 0
        self.replaced = self.decoded = 0
        self.last_seen_ns: int | None = None
        self._condition = Condition()
        self._stop = Event()
        self._pending: tuple[Frame, int] | None = None
        self._wait = Distribution(2048)
        self._retention = Distribution(2048)
        self._done = False
        self._error: BaseException | None = None
        self._error_observed = False
        self._thread: Thread | None = None
        if isinstance(source, VideoFileSource):
            source.realtime_minimum_ns = self._minimum_ns

    def _minimum_ns(self) -> int:
        if self.anchor_ns is None:
            return self.start_ns
        # Acquisition budget, not an extension to any downstream freshness gate.
        minimum = self.observation_anchor + perf_counter_ns() - self.anchor_ns - 50_000_000
        # Let the end boundary through so the iterator terminates without decoding
        # the remainder of a longer input file.
        return min(minimum, self.end_ns) if self.end_ns is not None else minimum

    @property
    def skipped_conversion(self) -> int:
        return self.source.skipped_conversion if isinstance(self.source, VideoFileSource) else 0

    def _run(self) -> None:
        try:
            previous_sequence = previous_ns = -1
            source_id: str | None = None
            for item in self.source:
                if self._stop.is_set():
                    break
                if isinstance(item, SourceIssue):
                    raise LabError("REALTIME_SOURCE_ISSUE")
                identity = item.identity
                if (
                    identity.sequence <= previous_sequence
                    or identity.observation_ns <= previous_ns
                    or (source_id is not None and identity.source_id != source_id)
                ):
                    raise LabError("REALTIME_SOURCE_DISCONTINUITY")
                previous_sequence, previous_ns = identity.sequence, identity.observation_ns
                self.last_seen_ns = previous_ns
                source_id = identity.source_id
                if previous_ns < self.start_ns:
                    continue
                if self.end_ns is not None and previous_ns >= self.end_ns:
                    break
                if self.anchor_ns is None:
                    self.anchor_ns = perf_counter_ns()
                    self.observation_anchor = previous_ns
                due = self.anchor_ns + previous_ns - self.observation_anchor
                if self._stop.wait(max(0, due - perf_counter_ns()) / 1e9):
                    break
                with self._condition:
                    self.decoded += 1
                    self.replaced += self._pending is not None
                    self._pending = (item, perf_counter_ns())
                    self._condition.notify()
        except BaseException as error:
            with self._condition:
                self._error = error
        finally:
            try:
                self.source.close()
            except BaseException as error:
                with self._condition:
                    self._error = self._error or error
            with self._condition:
                self._done = True
                self._condition.notify_all()

    def __iter__(self) -> Iterator[Frame | SourceIssue]:
        if self._thread is not None:
            raise RuntimeError("Latest source is single use")
        self._thread = Thread(target=self._run, name="sentinel-acquisition")
        self._thread.start()
        while True:
            started = perf_counter_ns()
            with self._condition:
                self._condition.wait_for(lambda: self._pending is not None or self._done)
                self._wait.add(perf_counter_ns() - started)
                if self._error is not None:
                    self._error_observed = True
                    raise self._error
                item, self._pending = self._pending, None
                if item is None:
                    return
                frame, offered = item
                self._retention.add(perf_counter_ns() - offered)
            yield frame

    def timing(self) -> dict[str, object]:
        with self._condition:
            return {
                "acquisition_wait": self._wait.summary(),
                "delivered_mailbox_retention": self._retention.summary(),
            }

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
        else:
            self.source.close()
        with self._condition:
            self._pending = None
            if self._error is not None and not self._error_observed:
                self._error_observed = True
                raise self._error
